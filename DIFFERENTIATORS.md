# Key Differentiators & Adoption Plan

## 1. Identity-Linked Joint-Window Fusion
Unlike traditional SIEM/UEBA platforms that only look at network traffic, or fraud engines that only look at transactions, PRAHARI looks at both simultaneously across a sliding 15-minute window. 
*   **The differentiator**: A login from a new IP (low confidence anomaly) + a transaction to a new beneficiary (low confidence anomaly) happening within 10 minutes to the *same identity* creates a high-confidence Fused Alert. This directly reduces false positives and bridges the SOC/Fraud team gap.

## 2. Regulatory-Aligned Explainability (RAG)
Every alert in PRAHARI doesn't just say "Score: 92%". It uses a RAG pipeline querying ChromaDB to cite the specific **RBI Cyber Security Framework** control that the anomaly violates.
*   **The differentiator**: Reduces the "black box" nature of AI. Alerts are immediately actionable and mapped to compliance frameworks, dramatically speeding up regulatory incident reporting.

## 3. Pragmatic PQC (Post-Quantum) Strategy
Instead of claiming to implement a fully quantum-proof vault in 4 days, PRAHARI takes the pragmatic, NIST-recommended first step: **Cryptographic Inventory and Monitoring**. 
*   **The differentiator**: We dynamically classify live TLS handshakes against FIPS 203/204/205 standards and flag "Harvest Now, Decrypt Later" (HNDL) exposure when sensitive data traverses legacy cryptography. It's a real-world, deployable first step.

## Adoption Plan
1. **Phase 1 (Shadow Mode)**: Deploy PRAHARI listeners alongside existing Kafka traffic (read-only). Tune the Identity Fusion Job sliding window parameters without affecting blocking logic.
2. **Phase 2 (Analyst Augmentation)**: Route Fused Alerts to Tier-2 SOC analysts. Use the RAG explanation drawer to speed up their triage time.
3. **Phase 3 (Active Interception)**: Once false positive rates hit target thresholds, wire the high-severity Fusion alerts back into the transaction gateway for active blocking.
