FROM jenkins/jenkins:lts-jdk17

USER root

# ── Python 3 + test essentials ──────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl wget \
    && rm -rf /var/lib/apt/lists/*

# ── API test deps (no browser) ──────────────────────────
RUN pip3 install --break-system-packages \
    pytest>=7.0 \
    pytest-timeout \
    pytest-xdist \
    requests \
    httpx \
    allure-pytest

# ── (Optional) Playwright for E2E — uncomment if server has 2G+ free RAM
# RUN pip3 install --break-system-packages playwright \
#     && python3 -m playwright install chromium --with-deps

USER jenkins

# ── Install Jenkins plugins via install-plugins.sh ──────
# Allure, Pipeline, Git, Blue Ocean, JUnit
RUN jenkins-plugin-cli --plugins \
    "allure-jenkins-plugin:latest" \
    "blueocean:latest" \
    "pipeline-stage-view:latest" \
    "git:latest" \
    "junit:latest" \
    "email-ext:latest" \
    "credentials-binding:latest"
