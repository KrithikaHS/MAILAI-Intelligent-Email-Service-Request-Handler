import os, glob, imaplib, email, logging, smtplib, pickle, textwrap
from email.header import decode_header
from email.mime.text import MIMEText
from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer
import faiss
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from transformers import pipeline

load_dotenv()
EMAIL_USER      = os.getenv("EMAIL_USER")
EMAIL_PASS      = os.getenv("EMAIL_PASS")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")     
KB_FOLDER       = "./kb"                          
EMBED_MODEL_NAME= "all-MiniLM-L6-v2"             
INDEX_FILE      = "./kb_index.faiss"
META_FILE       = "./kb_meta.pkl"

logging.basicConfig(level=logging.INFO)

ALLOWED_DOMAINS = ["yourcompany.com", ".edu", ".org", "gmail.com>"]

RESPONSIBLE_CONTACTS = {
    "it_support": {
        "name": "Alice Johnson",
        "phone": "555-123-4567"
    },
    "hr": {
        "name": "Robert Singh",
        "phone": "555-234-5678"
    },
    "payroll": {
        "name": "Dana Kim",
        "phone": "555-345-6789"
    },
    "benefits": {
        "name": "Marcus Lee",
        "phone": "555-456-7890"
    },
    "general": {
        "name": "Helpdesk Team",
        "phone": "555-000-0000"
    }
}

BASE_RESPONSES = {
    "it_support": (
        "Thanks for contacting IT Support. "
        "Please try restarting your device and checking your VPN connection. "
        "If the issue persists, we’ll get back to you shortly."
    ),
    "hr": (
        "Thank you for your message. For HR-related concerns such as policies, onboarding, or documentation, "
        "our HR team will review and follow up with you."
    ),
    "payroll": (
        "We’ve received your payroll query. If this is about a missing payment or tax document, "
        "rest assured it is being looked into."
    ),
    "benefits": (
        "Thanks for reaching out about benefits. If this is regarding insurance, leave, or wellness programs, "
        "we'll respond soon with more details."
    ),
    "general": (
        "Thank you for contacting us. Your message has been received and will be routed to the right team."
    )
}

classifier = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli")

def build_vector_store():
    embedder = SentenceTransformer(EMBED_MODEL_NAME)
    docs, meta = [], []
    for path in glob.glob(os.path.join(KB_FOLDER, "*")):
        with open(path, encoding="utf-8") as f:
            text = f.read()
            for chunk in text.split("\n\n"):
                chunk = chunk.strip()
                if chunk:
                    docs.append(chunk)
                    meta.append({"source": os.path.basename(path)})
    if not docs:
        raise RuntimeError("KB folder is empty!")
    embeddings = embedder.encode(docs, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, INDEX_FILE)
    with open(META_FILE, "wb") as f:
        pickle.dump({"docs": docs, "meta": meta}, f)
    logging.info("Vector store built with %d chunks", len(docs))

def load_vector_store():
    if not (os.path.exists(INDEX_FILE) and os.path.exists(META_FILE)):
        build_vector_store()
    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, "rb") as f:
        store = pickle.load(f)
    embedder = SentenceTransformer(EMBED_MODEL_NAME)
    return embedder, index, store

EMBEDDER, INDEX, STORE = load_vector_store()
LLM = ChatOpenAI(api_key=OPENAI_API_KEY, temperature=0.3)

def rag_answer(query: str, k: int = 3) -> str | None:
    q_emb = EMBEDDER.encode([query])
    D, I = INDEX.search(q_emb, k)
    hit_chunks = [STORE["docs"][idx] for idx in I[0] if D[0][list(I[0]).index(idx)] < 1.0]
    if not hit_chunks:
        return None

    context = "\n\n---\n\n".join(hit_chunks[:k])
    prompt = f"""
You are a helpful internal support assistant.
Use the context below to answer the employee's question.
If you are unsure, say you are unsure and escalate.

Context:
{context}

Employee question:
{query}

Answer:
"""
    chat = LLM([SystemMessage(content="You are MailAI, an internal assistant."),
                HumanMessage(content=prompt)])
    return textwrap.dedent(chat.content).strip()

def is_allowed_domain(addr):
    """Check if the email domain is in the list of allowed domains."""
    domain = addr.split('@')[-1].lower()
    print(domain)
    return any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS)

def decode_email_subject(raw):
    """Decode a potentially encoded email subject line."""
    if not raw:
        return ""
    decoded_parts = decode_header(raw)
    subject = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                subject += part.decode(encoding or "utf-8", errors="ignore")
            except Exception:
                subject += part.decode("utf-8", errors="ignore")
        else:
            subject += part
    return subject.strip()

def extract_email_body(msg):
    """Extract the plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_dispo = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_dispo:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore").strip()
                except:
                    continue
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore").strip()
        except:
            pass
    return ""

def classify_email(subject, body):
    """Classify email content using zero-shot classification."""
    labels = list(BASE_RESPONSES.keys())
    try:
        result = classifier(subject + "\n" + body, labels)
        return result["labels"][0] if result["scores"][0] > 0.5 else "general"
    except Exception as e:
        logging.warning("Classification failed: %s", e)
        return "general"

def send_email(to_addr, subj, body):
    """Send an email using SMTP."""
    try:
        msg = MIMEText(body)
        msg["From"] = EMAIL_USER
        msg["To"] = to_addr
        msg["Subject"] = subj

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [to_addr], msg.as_string())

        logging.info("Sent response to %s", to_addr)
    except Exception as e:
        logging.error("Failed to send email to %s: %s", to_addr, e)


def generate_auto_response(category: str, full_email_text: str) -> str:
    ai_solution = rag_answer(full_email_text)
    if ai_solution:
        response = ai_solution
    else:
        response = BASE_RESPONSES.get(
            category,
            "Thank you for contacting us. We’ll respond as soon as we can."
        )
    contact = RESPONSIBLE_CONTACTS.get(category)
    if contact:
        response += f"\n\nFor immediate assistance, contact {contact['name']} at {contact['phone']}."
    return response

def process_unseen_emails():
    
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(EMAIL_USER, EMAIL_PASS)
        imap.select("inbox")
        typ, data = imap.search(None, "UNSEEN")
        for eid in data[0].split():
            typ, msg_data = imap.fetch(eid, "(RFC822)")
            for part in msg_data:
                if not isinstance(part, tuple):
                    continue
                msg = email.message_from_bytes(part[1])
                subj = decode_email_subject(msg.get("Subject"))
                body = extract_email_body(msg)
                full_text = f"{subj}\n\n{body}".strip()

                category = classify_email(subj, body)
                logging.info("Classified as %s", category)

                reply_to = msg.get("Reply-To") or msg.get("From")
                if not reply_to or "noreply" in reply_to.lower() or not is_allowed_domain(reply_to):
                    logging.info("Skipping address %s", reply_to)
                    continue

                reply_body = generate_auto_response(category, full_text)
                send_email(reply_to, "Re: " + subj, reply_body)
        imap.logout()
    except Exception as e:
        logging.error("Processing failed: %s", e)

if __name__ == "__main__":
    logging.info("MailAI RAG responder started")
    process_unseen_emails()
