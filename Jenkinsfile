pipeline {
    agent any

    environment {
        NODE_KEY   = "${NODE_KEY}"    // set per laptop in Jenkins globals
        SERVER_IP  = "100.64.0.1"
        VENV_DIR   = "/opt/pocl-venv" // outside workspace — survives builds
    }

    triggers { githubPush() }

    stages {

        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install deps') {
            // Only runs when requirements.txt actually changes
            when {
                anyOf {
                    changeset "requirements.txt"
                    not { fileExists("/opt/pocl-venv/bin/activate") }
                }
            }
            steps {
                sh '''
                    python3 -m venv /opt/pocl-venv
                    /opt/pocl-venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Train') {
            steps {
                sh '''
                    /opt/pocl-venv/bin/python hospital_node_client.py \
                        --node ${NODE_KEY} --train_only --epochs 10
                '''
            }
        }

        stage('Validate') {
            steps {
                script {
                    def meta = readJSON file: 'output/metadata.json'
                    if ((meta.val_accuracy as Float) < 0.75)
                        error("Accuracy too low: ${meta.val_accuracy}")
                    echo "Accuracy: ${meta.val_accuracy} ✔"
                }
            }
        }

        stage('Send to server') {
            steps {
                sh '''
                    /opt/pocl-venv/bin/python hospital_node_client.py \
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