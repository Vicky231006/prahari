# RBI Cyber Security Framework Controls (Paraphrased Summaries)
# Mapped to Prahari alert signatures for semantic/metadata RAG retrieval

RBI_CONTROLS = [
    {
        "id": "RBI-CS-01",
        "control_no": "8.1",
        "title": "User Access Control and Centralized Authentication",
        "summary": "Enforce strong authentication mechanisms, session timeout policies, and centralized logging of all user activities including administrative access. Monitor for abnormal logon patterns.",
        "keywords": ["login", "authentication", "failed_login", "brute_force", "credential_stuffing"]
    },
    {
        "id": "RBI-CS-02",
        "control_no": "8.3",
        "title": "Privileged Access Monitoring",
        "summary": "Control and monitor administrative activities. Track execution of privileged commands, database alterations, and data access by privileged users. Flag abnormal activity.",
        "keywords": ["privileged_cmd", "privileged_account", "insider_collusion", "unusual_data_access"]
    },
    {
        "id": "RBI-CS-03",
        "control_no": "3.1",
        "title": "Network Security and Boundary Defence",
        "summary": "Implement firewalls, intrusion detection/prevention systems (IDS/IPS), and continuous logging of traffic. Monitor for reconnaissance attempts, unauthorized scans, and lateral movement.",
        "keywords": ["port_scan", "scanning", "network_recon", "lateral_movement"]
    },
    {
        "id": "RBI-CS-04",
        "control_no": "4.2",
        "title": "Data Loss Prevention (DLP)",
        "summary": "Monitor and control outbound data transmission channels to prevent unauthorized data leakage. Restrict bulk egress transfers especially to external destinations.",
        "keywords": ["exfiltration", "data_leak", "bulk_egress", "bulk_external_egress"]
    },
    {
        "id": "RBI-CS-05",
        "control_no": "10.1",
        "title": "Cryptographic Key Management & Encryption Standards",
        "summary": "Secure cryptographic operations by utilizing modern algorithms. Decommission outdated protocol ciphers (RSA, ECC under 256-bit) to prevent cryptanalysis attacks.",
        "keywords": ["legacy_crypto", "hndl_exposure", "tls_handshake", "key_exchange", "signature_algo"]
    },
    {
        "id": "RBI-CS-06",
        "control_no": "13.2",
        "title": "Security Correlation & Incident Response",
        "summary": "Correlate distinct infrastructure alerts, behavioral anomalies, and transaction parameters. Rapidly identify multi-channel attack campaigns to minimize false positives.",
        "keywords": ["fusion_alerts", "joint_window", "impossible_travel", "new_device", "new_beneficiary"]
    },
    {
        "id": "RBI-CS-07",
        "control_no": "6.4",
        "title": "Transaction Security Controls",
        "summary": "Verify authenticity of high-value transactions. Cross-examine behavioral signals, geolocation deviations, and device changes before authorizing payment channel usage.",
        "keywords": ["transaction", "upi", "neft", "imps", "high_value_txn", "new_beneficiary_txn"]
    }
]
