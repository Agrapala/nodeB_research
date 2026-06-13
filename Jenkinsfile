pipeline {
    agent any

    environment {
        NODE_KEY  = "${NODE_KEY}"
        SERVER_IP = "100.64.0.1"
        VENV_DIR  = "${WORKSPACE}/.venv"
        HASH_FILE = "${WORKSPACE}/.venv/requirements.hash"
    }

    triggers { githubPush() }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Detect requirements change') {
            steps {
                script {
                    def currentHash = sh(
                        script: "sha256sum requirements.txt | awk '{print \$1}'",
                        returnStdout: true
                    ).trim()

                    def oldHash = ""
                    if (fileExists(env.HASH_FILE)) {
                        oldHash = readFile(env.HASH_FILE).trim()
                    }

                    env.REQS_CHANGED = (currentHash != oldHash).toString()
                    env.CURRENT_HASH = currentHash

                    echo "Requirements changed: ${env.REQS_CHANGED}"
                }
            }
        }

        stage('Setup venv + install deps') {
            steps {
                sh '''
                    if [ ! -d "$VENV_DIR" ]; then
                        echo "Creating virtualenv..."
                        python3 -m venv "$VENV_DIR"
                    fi

                    if [ "$REQS_CHANGED" = "true" ]; then
                        echo "Installing dependencies..."
                        $VENV_DIR/bin/pip install -r requirements.txt

                        mkdir -p $VENV_DIR
                        echo "$CURRENT_HASH" > $HASH_FILE
                    else
                        echo "No dependency changes detected. Skipping install."
                    fi
                '''
            }
        }

        stage('Train') {
            steps {
                sh '''
                    $VENV_DIR/bin/python hospital_node_client.py \
                        --node ${NODE_KEY} --train_only --epochs 10
                '''
            }
        }

        stage('Validate') {
            steps {
                script {
                    def meta = readJSON file: 'output/metadata.json'
                    if ((meta.val_accuracy as Float) < 0.75) {
                        error("Accuracy too low: ${meta.val_accuracy}")
                    }
                    echo "Accuracy: ${meta.val_accuracy} ✔"
                }
            }
        }

        stage('Send to server') {
            steps {
                sh '''
                    $VENV_DIR/bin/python hospital_node_client.py \
                        --node ${NODE_KEY} --server_ip ${SERVER_IP} --send_only
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'output/metadata.json',
                             allowEmptyArchive: true
        }
    }
}