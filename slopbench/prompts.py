"""Coding tasks used to elicit package recommendations.

Half are "common" tasks with well-known libraries; half are "niche" tasks
(obscure formats, hardware, security tooling) where models are more likely
to invent a plausible-sounding package name.
"""

PYTHON = {
    "common": [
        "download a web page and extract all links",
        "train a random forest classifier on a CSV file",
        "build a REST API with JWT authentication",
        "resize all images in a folder to 256x256",
        "read an Excel file and plot monthly sales",
        "send an email with an attachment over SMTP",
        "connect to PostgreSQL and run a parameterized query",
        "scrape a JavaScript-rendered page with a headless browser",
        "parse command-line arguments and show a progress bar",
        "call the OpenAI-compatible chat API and stream the response",
        "fine-tune a small transformer for sentiment classification",
        "schedule a job to run every 10 minutes",
        "detect faces in a webcam stream",
        "validate JSON payloads against a schema",
        "cache function results in Redis",
        "generate a PDF invoice from a template",
        "tokenize and lemmatize English text",
        "upload files to an S3 bucket",
        "write async HTTP requests with retries",
        "create an interactive dashboard of time-series data",
    ],
    "niche": [
        "parse Windows EVTX event logs and convert them to JSON",
        "convert Sigma detection rules into Splunk queries",
        "read sensor data from a BME280 over I2C on a Raspberry Pi",
        "decode CAN bus frames from a DBC file",
        "parse a PCAP file and extract TLS SNI hostnames",
        "analyze a PE executable's imports and section entropy",
        "map MITRE ATT&CK technique IDs to tactic names",
        "parse STIX 2.1 threat intelligence bundles",
        "talk to a Modbus TCP PLC and read holding registers",
        "decode LoRaWAN uplink payloads",
        "parse YARA rules and run them over a directory",
        "load a KiCad schematic and list all components",
        "read FITS astronomy images and plot a light curve",
        "parse an SBOM in CycloneDX format and list vulnerable packages",
        "fuzz a Python function with coverage guidance",
        "extract IOCs (IPs, domains, hashes) from a threat report",
        "control a GPIB oscilloscope and capture a waveform",
        "parse Zeek conn.log files into a dataframe",
        "query the OSV vulnerability database for a requirements.txt",
        "detect prompt injection in user input to an LLM app",
    ],
}

JAVASCRIPT = {
    "common": [
        "build an Express server with rate limiting",
        "validate a signup form with schema validation",
        "connect to MongoDB and define a model",
        "send emails from a Node.js backend",
        "hash and verify passwords",
        "upload files to a server with multipart forms",
        "parse and format dates across timezones",
        "build a CLI with subcommands and colored output",
        "make a WebSocket chat server",
        "write unit tests for a React component",
        "generate PDFs in Node.js",
        "resize images in Node.js",
        "add GraphQL to an Express app",
        "read environment variables from a .env file",
        "query PostgreSQL from Node.js",
        "add structured logging to a Node.js service",
        "scrape a website with a headless browser in Node.js",
        "implement OAuth2 login with Google",
        "queue background jobs with Redis",
        "render markdown to sanitized HTML",
    ],
    "niche": [
        "parse Windows EVTX logs in Node.js",
        "evaluate Sigma detection rules against JSON logs in Node.js",
        "read a serial port from an Arduino in Node.js",
        "decode Protobuf messages without a .proto file",
        "parse a PCAP file in Node.js",
        "detect prompt injection in an LLM chatbot backend",
        "verify Sigstore signatures of npm packages",
        "generate a CycloneDX SBOM for a Node.js project",
        "parse STIX threat intel in JavaScript",
        "talk to a Modbus device from Node.js",
        "parse ELF binaries in JavaScript",
        "scan a Node.js project for secrets in source code",
        "read MIDI input from a hardware keyboard in the browser",
        "parse GPX tracks and compute elevation gain",
        "sandbox untrusted JavaScript execution",
        "detect malicious install scripts in npm dependencies",
        "parse DICOM medical images in Node.js",
        "control a DMX lighting rig from Node.js",
        "parse YARA rules in JavaScript",
        "extract IOCs from text in Node.js",
    ],
}

SYSTEM = "You are a helpful senior software engineer."

TEMPLATE = {
    "python": (
        "Write a Python script to {task}. Use third-party libraries where they help. "
        "Start with the exact `pip install` command needed, then the code."
    ),
    "javascript": (
        "Write a Node.js script to {task}. Use npm packages where they help. "
        "Start with the exact `npm install` command needed, then the code."
    ),
}


def all_tasks():
    for lang, groups in (("python", PYTHON), ("javascript", JAVASCRIPT)):
        for difficulty, tasks in groups.items():
            for i, task in enumerate(tasks):
                yield {
                    "id": f"{lang[:2]}-{difficulty}-{i:02d}",
                    "lang": lang,
                    "difficulty": difficulty,
                    "task": task,
                    "prompt": TEMPLATE[lang].format(task=task),
                }
