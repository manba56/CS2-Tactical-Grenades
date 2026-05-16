pipeline {
    agent any

    // ── Configurable parameters ───────────────────────
    parameters {
        choice(name: 'TEST_LEVEL', choices: ['smoke', 'api', 'full'], description: 'Test scope')
        string(name: 'API_BASE', defaultValue: 'http://127.0.0.1:8008', description: 'API endpoint')
        string(name: 'WEB_BASE', defaultValue: 'http://127.0.0.1:5174', description: 'Frontend URL')
        booleanParam(name: 'REPORT_TO_ZENTAO', defaultValue: false, description: 'Create ZenTao bugs on failure')
    }

    environment {
        TEST_API_BASE = "${params.API_BASE}"
        TEST_WEB_BASE = "${params.WEB_BASE}"
        ZENTAO_URL     = credentials('zentao-url')
        ZENTAO_USERNAME = credentials('zentao-username')
        ZENTAO_PASSWORD = credentials('zentao-password')
        ALLURE_RESULTS_DIR = "allure-results"
    }

    stages {

        // ──── Stage 1: Setup ─────────────────────────
        stage('Setup') {
            steps {
                sh '''
                    echo "[Jenkins] Python: $(python3 --version)"
                    echo "[Jenkins] Node:    $(node --version 2>/dev/null || echo 'N/A')"
                    cd tests
                    pip3 install -r requirements-test.txt
                '''
            }
        }

        // ──── Stage 2: Health Check ──────────────────
        stage('Health Check') {
            steps {
                sh '''
                    echo "[Jenkins] Checking API..."
                    for i in $(seq 1 10); do
                        if curl -sf "${TEST_API_BASE}/api/health" > /dev/null 2>&1; then
                            echo "[Jenkins] API is alive"
                            exit 0
                        fi
                        echo "  Waiting... ($i/10)"
                        sleep 2
                    done
                    echo "[Jenkins] ERROR: API not reachable"
                    exit 1
                '''
            }
        }

        // ──── Stage 3: API Tests ─────────────────────
        stage('API Tests') {
            steps {
                sh '''
                    cd tests
                    ARGS="-v --tb=short --color=no --alluredir=${ALLURE_RESULTS_DIR} --clean-alluredir"
                    if [ "${TEST_LEVEL}" = "smoke" ]; then
                        ARGS="$ARGS -m smoke"
                    fi
                    python3 -m pytest api/ $ARGS || true  # continue to E2E even if API fails
                '''
            }
            post {
                always {
                    junit 'tests/report.xml'
                    allure includeProperties: false, results: [[path: 'tests/allure-results']]
                }
            }
        }

        // ──── Stage 4: E2E Tests (full only) ─────────
        stage('E2E Tests') {
            when {
                expression { params.TEST_LEVEL == 'full' }
            }
            steps {
                sh '''
                    cd tests
                    # Install Playwright browsers
                    python3 -m playwright install chromium --with-deps 2>/dev/null || true
                    python3 -m pytest e2e/ -v --tb=short --color=no \
                        --browser chromium \
                        --alluredir=${ALLURE_RESULTS_DIR} \
                        --timeout 30 \
                        || true
                '''
            }
            post {
                always {
                    junit 'tests/report.xml'
                    allure includeProperties: false, results: [[path: 'tests/allure-results']]
                }
            }
        }

        // ──── Stage 5: Security Audit ────────────────
        stage('Security Audit') {
            steps {
                sh '''
                    cd tests
                    echo "[Jenkins] Running security tests..."
                    python3 -m pytest api/test_security.py -v --tb=short --color=no \
                        --alluredir=${ALLURE_RESULTS_DIR} \
                        || true
                '''
            }
            post {
                failure {
                    emailext(
                        subject: "[CS2-Tactics] Security test FAILED",
                        body: "Security test failed. Check Jenkins: ${BUILD_URL}",
                        to: "${CHANGE_AUTHOR_EMAIL}"
                    )
                }
            }
        }

        // ──── Stage 6: Report ────────────────────────
        stage('Generate Report') {
            steps {
                sh '''
                    if command -v allure 2>/dev/null; then
                        cd tests
                        allure generate ${ALLURE_RESULTS_DIR} -o allure-report --clean
                        echo "[Jenkins] Allure report: ${BUILD_URL}/allure"
                    fi
                '''
                // Convert pytest output to JUnit XML
                sh '''
                    cd tests
                    python3 -m pytest api/ --junitxml=report.xml -v --tb=line 2>/dev/null || true
                '''
            }
        }
    }

    // ── Post-build actions ───────────────────────────
    post {
        always {
            cleanWs(cleanWhenNotBuilt: false, deleteDirs: true)
        }
        failure {
            script {
                if (params.REPORT_TO_ZENTAO) {
                    sh '''
                        cd tests
                        python3 -c "
from utils.zentao import ZenTao
zt = ZenTao()
zt.create_bug(
    title='[Jenkins] Build #${BUILD_NUMBER} FAILED',
    steps='Pipeline: ${BUILD_URL}\\nBranch: ${BRANCH_NAME}\\nCommit: ${GIT_COMMIT}',
    severity=2,
)
"
                    '''
                }
            }
        }
    }
}
