

pipeline {
    agent any

    environment {
        NODE_KEY    = "${NODE_KEY}"
        SERVER_IP   = "100.64.0.1"
        SERVER_PORT = "8888"
        IMAGE       = "ghcr.io/Agrapala/pocl-node:latest"
        MIN_ACC     = "0.75"
        MIN_AUC     = "0.80"
        MIN_F1      = "0.72"
    }

    triggers {
        githubPush()             
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 2, unit: 'HOURS')   
        timestamps()
    }


    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "✔ Code checked out for Node ${NODE_KEY}"
                sh 'echo "Commit: $(git log -1 --pretty=format:\"%h — %s\")"'
            }
        }

        stage('Pull Docker image') {
            when {
                anyOf {
                    changeset "requirements.txt"
                    changeset "Dockerfile"
                    not { sh(script: "docker image inspect ${IMAGE} > /dev/null 2>&1", returnStatus: true) == 0 }
                }
            }
            steps {
                echo "Pulling updated image: ${IMAGE}"
                sh 'docker pull ${IMAGE}'
            }
        }

        stage('Train CNN') {
            steps {
                echo "Starting training for Node ${NODE_KEY}..."
                sh '''
                    docker run --rm \
                        --name pocl-train-${NODE_KEY}-${BUILD_NUMBER} \
                        -v ${WORKSPACE}/data/Node_${NODE_KEY}:/app/data/Node_${NODE_KEY}:ro \
                        -v ${WORKSPACE}/output:/app/output \
                        ${IMAGE} \
                            --node       ${NODE_KEY} \
                            --train_only \
                            --epochs     10
                '''
            }
        }

        stage('Validate model') {
            steps {
                script {
                    def metaFile = "${WORKSPACE}/output/metadata.json"

                    if (!fileExists(metaFile)) {
                        error("metadata.json not found — training may have failed")
                    }

                    def meta  = readJSON file: metaFile
                    def acc   = meta.val_accuracy  as Float
                    def auc   = meta.val_auc        as Float
                    def f1    = meta.val_f1         as Float
                    def prec  = meta.val_precision  as Float
                    def rec   = meta.val_recall     as Float

                    echo "════════════════════════════════"
                    echo "  Validation results — Node ${NODE_KEY}"
                    echo "  Hospital : ${meta.name}"
                    echo "  Samples  : ${meta.num_samples}"
                    echo "  Epochs   : ${meta.epochs_trained}"
                    echo "  Accuracy : ${acc}"
                    echo "  AUC      : ${auc}"
                    echo "  Precision: ${prec}"
                    echo "  Recall   : ${rec}"
                    echo "  F1       : ${f1}"
                    echo "════════════════════════════════"

                    def errors = []
                    if (acc < MIN_ACC.toFloat()) errors << "Accuracy ${acc} < ${MIN_ACC}"
                    if (auc < MIN_AUC.toFloat()) errors << "AUC ${auc} < ${MIN_AUC}"
                    if (f1  < MIN_F1.toFloat())  errors << "F1 ${f1} < ${MIN_F1}"

                    if (errors) {
                        error("Model quality gate FAILED:\n  " + errors.join("\n  "))
                    }

                    echo "✔ Model passed all quality gates"
                }
            }
        }

        stage('Send model to server') {
            steps {
                echo "Sending model to PoCL server at ${SERVER_IP}:${SERVER_PORT}..."
                sh '''
                    docker run --rm \
                        --name pocl-send-${NODE_KEY}-${BUILD_NUMBER} \
                        -v ${WORKSPACE}/output:/app/output \
                        ${IMAGE} \
                            --node        ${NODE_KEY} \
                            --server_ip   ${SERVER_IP} \
                            --server_port ${SERVER_PORT} \
                            --send_only
                '''
                echo "✔ Model sent successfully"
            }
        }
    }

    post {

        success {
            script {
                def meta = readJSON file: "${WORKSPACE}/output/metadata.json"
                echo """
                ╔══════════════════════════════════════╗
                  Pipeline SUCCESS — Node ${NODE_KEY}
                  Hospital : ${meta.name}
                  Accuracy : ${meta.val_accuracy}
                  AUC      : ${meta.val_auc}
                  F1       : ${meta.val_f1}
                ╚══════════════════════════════════════╝
                """
            }
            archiveArtifacts artifacts: 'output/metadata.json', allowEmptyArchive: false
        }

        failure {
            echo "✖ Pipeline FAILED for Node ${NODE_KEY} — check logs above"
            archiveArtifacts artifacts: 'output/metadata.json', allowEmptyArchive: true
        }

        always {
            sh '''
                docker rm -f pocl-train-${NODE_KEY}-${BUILD_NUMBER} 2>/dev/null || true
                docker rm -f pocl-send-${NODE_KEY}-${BUILD_NUMBER}  2>/dev/null || true
            '''
        }
    }
}