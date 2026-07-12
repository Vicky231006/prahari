"""
Main entry point for the PRAHARI Streaming Processor.

Subscribes to:
- security-telemetry
- transaction-events
- tls-handshake

Processes incoming streams, runs detection rules, evaluates fusion state,
classifies cryptography, updates Redis caches, and writes alerts back to Kafka.
"""
import json
import os
import signal
import sys
import time
from confluent_kafka import Consumer, KafkaError, Producer

from .config import settings
from .redis_client import RedisClient
from .fusion.job import IdentityFusionJob
from .quantum.job import CryptoInventoryJob

def main():
    print("=" * 60)
    print("PRAHARI Stream Processing Engine")
    print("=" * 60)

    # 1. Initialize Redis feature store/caching client
    print(f"[init] Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}...")
    redis_client = RedisClient()
    try:
        redis_client.client.ping()
        print("[init] Redis connection verified")
    except Exception as e:
        print(f"[init] Redis connection failed: {e}")
        sys.exit(1)

    # 2. Initialize Kafka Producer (for emitting alerts)
    print(f"[init] Connecting Kafka Producer to {settings.KAFKA_BOOTSTRAP_SERVERS}...")
    producer_conf = {
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "client.id": "prahari-streaming-producer",
        "acks": "all"
    }
    try:
        producer = Producer(producer_conf)
        print("[init] Kafka Producer initialized")
    except Exception as e:
        print(f"[init] Kafka Producer setup failed: {e}")
        sys.exit(1)

    # 3. Instantiate stream jobs
    fusion_job = IdentityFusionJob(redis_client, producer)
    # Check if we have an env override for classifier URL
    classifier_host = os.getenv("FUSION_CLASSIFIER_URL")
    if classifier_host:
        fusion_job.classifier_url = f"{classifier_host}/internal/fusion/score"
    print(f"[init] Identity Fusion Job initialized (Classifier: {fusion_job.classifier_url})")

    quantum_job = CryptoInventoryJob(redis_client, producer)
    print("[init] Crypto Inventory Job initialized")

    # 4. Initialize Kafka Consumer
    print(f"[init] Connecting Kafka Consumer to {settings.KAFKA_BOOTSTRAP_SERVERS}...")
    consumer_conf = {
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "prahari-streaming-group",
        "auto.offset.reset": "latest",
        "enable.auto.commit": True
    }
    
    try:
        consumer = Consumer(consumer_conf)
        # Subscribe to all three core telemetry topics
        topics = [settings.TOPIC_SECURITY, settings.TOPIC_TRANSACTIONS, settings.TOPIC_TLS]
        consumer.subscribe(topics)
        print(f"[init] Subscribed to topics: {topics}")
    except Exception as e:
        print(f"[init] Kafka Consumer setup failed: {e}")
        sys.exit(1)

    # Graceful shutdown handler
    running = True
    def stop_processing(signum, frame):
        nonlocal running
        print("\n[shutdown] Stopping stream processing...")
        running = False

    signal.signal(signal.SIGINT, stop_processing)
    signal.signal(signal.SIGTERM, stop_processing)

    print("[running] Streaming engine listening for telemetry. Ctrl+C to exit.")
    print("=" * 60)

    # Main poll loop
    while running:
        msg = consumer.poll(timeout=0.5)
        if msg is None:
            continue

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event (not a failure)
                continue
            else:
                print(f"[kafka-err] Consumer error: {msg.error()}")
                time.sleep(1)
                continue

        # Parse message
        topic = msg.topic()
        try:
            value_str = msg.value().decode("utf-8")
            event = json.loads(value_str)
        except Exception as e:
            print(f"[error] Failed to parse message on topic {topic}: {e}")
            continue

        # Route event to corresponding streaming job
        try:
            if topic == settings.TOPIC_SECURITY:
                fusion_job.process_security_event(event)
            elif topic == settings.TOPIC_TRANSACTIONS:
                fusion_job.process_transaction_event(event)
            elif topic == settings.TOPIC_TLS:
                quantum_job.process_tls_event(event)
        except Exception as e:
            print(f"[error] Exception during processing of event from {topic}: {e}")

    # Shutdown sequence
    print("[shutdown] Closing Kafka consumer...")
    consumer.close()
    print("[shutdown] Flushing Kafka producer...")
    producer.flush(timeout=5)
    print("[shutdown] Streaming engine stopped.")

if __name__ == "__main__":
    main()
