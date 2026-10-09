import io
import json
import urllib.request
import urllib.error
import urllib.parse
import sys

BASE_URL = "http://localhost:8003"
TOKEN = None

def get_auth_token():
    global TOKEN
    username = "test_eval_user"
    password = "StrongPassword123!"

    # Try registering
    reg_data = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/auth/register", data=reg_data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        # User may already exist, ignore
        pass

    # Login
    login_data = urllib.parse.urlencode({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=login_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        TOKEN = body["access_token"]
    return TOKEN

def create_simple_pdf(text_lines: list[str]) -> bytes:
    """Generate a minimal valid PDF-1.4 file with readable text without external libraries."""
    stream_content = "BT\n/F1 12 Tf\n50 750 Td\n14 TL\n"
    for line in text_lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({safe_line}) '\n"
    stream_content += "ET\n"
    stream_bytes = stream_content.encode("latin1")
    
    body = bytearray()
    body.extend(b"%PDF-1.4\n")
    
    offsets = [0]
    
    def add_obj(obj_str: str) -> int:
        offsets.append(len(body))
        data = obj_str.encode("latin1")
        body.extend(data)
        return len(offsets) - 1

    add_obj("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    add_obj("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    add_obj("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    add_obj(f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n{stream_content}endstream\nendobj\n")
    add_obj("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    xref_offset = len(body)
    body.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for off in offsets[1:]:
        body.extend(f"{off:010d} 00000 n \n".encode("latin1"))
    body.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1"))
    return bytes(body)

def upload_pdf(endpoint_url: str, filename: str, pdf_bytes: bytes):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: application/pdf\r\n\r\n")
    body.extend(pdf_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(endpoint_url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def evaluate_candidate(payload: dict):
    req = urllib.request.Request(f"{BASE_URL}/api/full-pipeline", data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def run_tests():
    print("=== STARTING COMPREHENSIVE TEST SUITE ===")
    token = get_auth_token()
    print(f"Authenticated successfully with JWT token: {token[:20]}...")

    # TEST: Root / and /demo endpoints serve UI
    print("\n[TEST] UI Endpoint availability: GET / and GET /demo")
    req_root = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req_root) as r:
        assert r.status == 200, f"Expected 200 for /, got {r.status}"
        html = r.read().decode("utf-8")
        assert "FairWork AI" in html
        print("PASS: GET / successfully serves FairWork AI UI")

    req_demo = urllib.request.Request(f"{BASE_URL}/demo")
    with urllib.request.urlopen(req_demo) as r:
        assert r.status == 200, f"Expected 200 for /demo, got {r.status}"
        print("PASS: GET /demo successfully serves FairWork AI UI")

    # TEST: /api/jobs catalog endpoint
    print("\n[TEST] Jobs catalog: GET /api/jobs")
    req_jobs = urllib.request.Request(f"{BASE_URL}/api/jobs")
    req_jobs.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req_jobs) as r:
        assert r.status == 200
        jobs = json.loads(r.read().decode("utf-8"))
        assert len(jobs) >= 15
        print(f"PASS: GET /api/jobs returned {len(jobs)} benchmark job roles")

    # TEST: Certificate PDF Upload Endpoint (/api/upload/certificate)
    print("\n[TEST] Certificate PDF Upload: POST /api/upload/certificate")
    cert_pdf = create_simple_pdf([
        "Certificate of Completion",
        "AWS Certified Data Engineer",
        "Verified competencies in PySpark, SQL, and ETL Pipelines"
    ])
    code_c, res_c = upload_pdf(f"{BASE_URL}/api/upload/certificate", "aws_cert.pdf", cert_pdf)
    print(f"Status: {code_c}, Extracted chars: {res_c.get('character_count')}")
    assert code_c == 200 and "PySpark" in res_c["text"]
    print("PASS: POST /api/upload/certificate successfully validated and extracted certificate text")

    # Certificate PDF Validation: non-PDF rejection
    code_inv, res_inv = upload_pdf(f"{BASE_URL}/api/upload/certificate", "invalid.txt", b"plain text")
    assert code_inv == 400
    print("PASS: Certificate upload rejects non-PDF with 400")

    # CASE F: Invalid non-PDF upload
    print("\n[TEST] Case F: Invalid non-PDF upload")
    code, res = upload_pdf(f"{BASE_URL}/api/upload/resume", "malicious.txt", b"This is just plain text, not a PDF header")
    assert code == 400, f"Expected 400 for non-pdf, got {code}"
    print("PASS: Non-PDF rejected with 400")

    # CASE G: Oversized PDF (>10MB)
    print("\n[TEST] Case G: Oversized PDF (>10MB)")
    oversized_data = b"%PDF-1.4\n" + b"A" * (11 * 1024 * 1024)
    code, res = upload_pdf(f"{BASE_URL}/api/upload/resume", "huge.pdf", oversized_data)
    assert code == 400, f"Expected 400 for oversized PDF, got {code}"
    print("PASS: Oversized PDF rejected with 400")

    # CASE H: Corrupted / Empty PDF
    print("\n[TEST] Case H: Corrupted / Empty PDF")
    code, res = upload_pdf(f"{BASE_URL}/api/upload/resume", "empty.pdf", b"")
    assert code == 400, f"Expected 400 for empty PDF, got {code}"
    
    code, res = upload_pdf(f"{BASE_URL}/api/upload/portfolio", "corrupt.pdf", b"%PDF-1.4\nCorrupted binary junk...")
    assert code == 400, f"Expected 400 for corrupted PDF, got {code}"
    print("PASS: Empty and Corrupted PDF rejected with 400")

    # CASE I: Remove and Replace PDF
    print("\n[TEST] Case I: Upload and Replace PDF")
    pdf_v1 = create_simple_pdf(["Initial Resume", "Python developer"])
    code1, res1 = upload_pdf(f"{BASE_URL}/api/upload/resume", "resume_v1.pdf", pdf_v1)
    assert code1 == 200 and "Python" in res1["text"]
    
    pdf_v2 = create_simple_pdf(["Updated Resume", "PySpark and Data Analysis specialist"])
    code2, res2 = upload_pdf(f"{BASE_URL}/api/upload/resume", "resume_v2.pdf", pdf_v2)
    assert code2 == 200 and "PySpark" in res2["text"]
    print("PASS: Replace PDF successfully updated extracted text")

    # CASE A: Basic candidate with no uploaded files
    print("\n[TEST] Case A: Basic candidate with no uploaded files")
    case_a_payload = {
        "candidate_id": "CASE_A_001",
        "experience_years": 2,
        "claimed_skills": ["Python", "FastAPI"],
        "portfolio_projects": [
            {"project_id": "proj_a1", "title": "API Service", "description": "Built REST APIs with Python and FastAPI"}
        ],
        "work_descriptions": [],
        "certificates": [],
        "code_samples": []
    }
    code, res = evaluate_candidate(case_a_payload)
    assert code == 200, f"Case A failed: {res}"
    print("PASS: Case A evaluated successfully without optional evidence")

    # CASE B: Candidate with structured evidence (Cert, Work, CodeSample, Projects), no PDFs
    print("\n[TEST] Case B: Candidate with structured evidence (cert, work, code sample, project)")
    case_b_payload = {
        "candidate_id": "CASE_B_001",
        "experience_years": 4,
        "claimed_skills": ["PySpark", "Data Analysis"],
        "portfolio_projects": [
            {"project_id": "proj_b1", "title": "Analytics Engine", "description": "ETL engine using PySpark for data analysis", "role": "Lead", "url": "https://example.com/project"}
        ],
        "work_descriptions": [
            {"work_id": "work_b1", "title": "Senior Data Engineer", "company": "DataCorp", "duration": "2 years", "description": "Built PySpark pipelines and SQL data models"}
        ],
        "certificates": [
            {"certificate_id": "cert_b1", "title": "Spark Developer Certificate", "issuer": "Databricks", "url": "https://databricks.com/cert/123", "description": "PySpark developer cert"}
        ],
        "code_samples": [
            {"sample_id": "code_b1", "title": "PySpark Repo", "url": "https://github.com/datacorp/spark-repo", "description": "PySpark data transformation scripts"}
        ]
    }
    code, res = evaluate_candidate(case_b_payload)
    assert code == 200, f"Case B failed: {res}"
    summary_b = res.get("evidence_summary", {})
    assert summary_b.get("work_experience_count") == 1
    assert summary_b.get("certificates_count") == 1
    assert summary_b.get("code_samples_count") == 1
    assert summary_b.get("projects_count") == 1
    print("PASS: Case B structured evidence fully registered and used")

    # CASE C: Candidate with resume PDF only
    print("\n[TEST] Case C: Candidate with resume PDF only")
    resume_c = create_simple_pdf([
        "Candidate C Resume",
        "Skills: PySpark, Data Analysis, Python",
        "Work Experience: 3 years building data pipelines with PySpark"
    ])
    code_up, res_up = upload_pdf(f"{BASE_URL}/api/upload/resume", "resume_c.pdf", resume_c)
    assert code_up == 200
    case_c_payload = {
        "candidate_id": "CASE_C_001",
        "experience_years": 3,
        "claimed_skills": ["PySpark", "Data Analysis"],
        "resume_text": res_up["text"],
        "resume_filename": res_up["filename"],
        "portfolio_projects": [],
        "work_descriptions": [],
        "certificates": [],
        "code_samples": []
    }
    code, res = evaluate_candidate(case_c_payload)
    assert code == 200
    assert res.get("evidence_summary", {}).get("resume_uploaded") is True
    print("PASS: Case C evaluated successfully with resume PDF only")

    # CASE D: Candidate with portfolio PDF only
    print("\n[TEST] Case D: Candidate with portfolio PDF only")
    portfolio_d = create_simple_pdf([
        "Portfolio Document for Candidate D",
        "Project: Big Data Pipeline",
        "Built an end-to-end PySpark ETL system for batch analytics"
    ])
    code_up, res_up = upload_pdf(f"{BASE_URL}/api/upload/portfolio", "portfolio_d.pdf", portfolio_d)
    assert code_up == 200
    case_d_payload = {
        "candidate_id": "CASE_D_001",
        "experience_years": 3,
        "claimed_skills": ["PySpark"],
        "portfolio_document_text": res_up["text"],
        "portfolio_document_filename": res_up["filename"],
        "portfolio_projects": [],
        "work_descriptions": [],
        "certificates": [],
        "code_samples": []
    }
    code, res = evaluate_candidate(case_d_payload)
    assert code == 200
    assert res.get("evidence_summary", {}).get("portfolio_doc_uploaded") is True
    print("PASS: Case D evaluated successfully with portfolio PDF only")

    # CASE E & MAIN END-TO-END: Candidate TEST001 with Resume PDF, Portfolio PDF, AND Certificate PDF
    print("\n[TEST] MAIN END-TO-END (Case E): Candidate TEST001 with Resume, Portfolio, AND Certificate PDF")
    resume_test001 = create_simple_pdf([
        "Resume of TEST001",
        "Role: Data Engineer",
        "Skills: PySpark, Data Analysis",
        "Work Experience: Test Company",
        "Built and maintained PySpark pipelines for large-scale data processing."
    ])
    code_r, res_r = upload_pdf(f"{BASE_URL}/api/upload/resume", "test001_resume.pdf", resume_test001)
    assert code_r == 200

    portfolio_test001 = create_simple_pdf([
        "Portfolio Document for TEST001",
        "Project: Data Processing Pipeline",
        "Built an ETL pipeline using PySpark to process large datasets."
    ])
    code_p, res_p = upload_pdf(f"{BASE_URL}/api/upload/portfolio", "test001_portfolio.pdf", portfolio_test001)
    assert code_p == 200

    cert_test001 = create_simple_pdf([
        "AWS Certification Credential",
        "Recipient: TEST001",
        "Certified in PySpark, Big Data Architecture, and ETL Systems"
    ])
    code_cert, res_cert = upload_pdf(f"{BASE_URL}/api/upload/certificate", "aws_test001_cert.pdf", cert_test001)
    assert code_cert == 200

    test001_payload = {
        "candidate_id": "TEST001",
        "experience_years": 3,
        "claimed_skills": ["PySpark", "Data Analysis"],
        "resume_text": res_r["text"],
        "resume_filename": res_r["filename"],
        "portfolio_document_text": res_p["text"],
        "portfolio_document_filename": res_p["filename"],
        "portfolio_projects": [
            {
                "project_id": "proj_t1",
                "title": "Data Processing Pipeline",
                "description": "Built an ETL pipeline using PySpark to process large datasets.",
                "role": "Data Engineer",
                "url": "https://github.com/test001/data-pipeline"
            }
        ],
        "work_descriptions": [
            {
                "work_id": "work_t1",
                "title": "Data Engineer",
                "company": "Test Company",
                "duration": "3 years",
                "description": "Built and maintained PySpark pipelines for large-scale data processing."
            }
        ],
        "certificates": [
            {
                "certificate_id": "cert_t1",
                "title": "AWS Certified Data Engineer",
                "issuer": "Amazon Web Services",
                "url": "https://aws.amazon.com/verification/123",
                "description": "Demonstrated data engineering competency with PySpark and cloud pipelines.",
                "certificate_text": res_cert["text"],
                "certificate_filename": res_cert["filename"]
            }
        ],
        "code_samples": [
            {
                "sample_id": "code_t1",
                "title": "PySpark Data Processing Repo",
                "url": "https://github.com/test001/pyspark-pipeline",
                "description": "Repository containing PySpark ETL pipeline implementation for processing large datasets."
            }
        ]
    }
    code, res = evaluate_candidate(test001_payload)
    print(f"\nTEST001 Result Status: {code}")
    print(f"Candidate ID: {res.get('candidate_id')}")
    print(f"Verified Skills: {json.dumps(res.get('verified_skills'), indent=2)}")
    print(f"Fairness Evaluation: {json.dumps(res.get('fairness'), indent=2)}")
    print(f"Evidence Summary: {json.dumps(res.get('evidence_summary'), indent=2)}")
    
    assert code == 200
    assert res.get("candidate_id") == "TEST001"
    
    # Verify that PySpark or Data Analysis was supported
    skills_map = {v["skill"].lower(): v["status"] for v in res.get("verified_skills", [])}
    assert any(s in ("supported", "weakly_supported") for s in skills_map.values()), "At least one skill must be verified!"
    
    summary = res.get("evidence_summary", {})
    assert summary.get("resume_uploaded") is True
    assert summary.get("portfolio_doc_uploaded") is True
    assert summary.get("projects_count") == 1
    assert summary.get("work_experience_count") == 1
    assert summary.get("certificates_count") == 1
    assert summary.get("code_samples_count") == 1
    assert any("with verified PDF" in s for s in summary.get("sources_used", []))
    print("\nALL TEST CASES (A through J, Certificate PDF upload, and Candidate TEST001) PASSED WITH FLYING COLORS!")

if __name__ == "__main__":
    run_tests()
