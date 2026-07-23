pipeline {
    agent any

    environment {
        REPO_URL    = 'https://github.com/Mayank1619/MainframeModernization.git'
        APP_BRANCH  = 'feature-testing-jenkins'      // branch with the Spring Boot app
        APP_PORT    = '8080'
    }

    stages {

        stage('Checkout App') {
            steps {
                dir('app') {
                    git branch: "${APP_BRANCH}", url: "${REPO_URL}"
                }
            }
        }

        stage('Build App') {
            steps {
                withMaven(
                    // Maven installation declared in the Jenkins "Global Tool Configuration"
                    maven: 'maven-3', // (1)
                    mavenLocalRepo: '.repository', // (2)
                    mavenSettingsConfig: 'my-maven-settings' // (3)
                ) {
                    sh '''
                    cd app
                    mvn -B -f src/api/pom.xml clean package -DskipTests
                    '''
                }
            }
        }

        stage('Start App') {
            steps {
                withMaven(
                    // Maven installation declared in the Jenkins "Global Tool Configuration"
                    maven: 'maven-3', // (1)
                    mavenLocalRepo: '.repository', // (2)
                    mavenSettingsConfig: 'my-maven-settings' // (3)
                ) {
                    sh """#!/bin/bash
                        export JENKINS_NODE_COOKIE=dontKillMe
                        cd app
                        nohup mvn -f src/api/pom.xml spring-boot:run > app.log 2>&1 &
                        echo \$! > app.log
                        echo "Waiting for app to become ready on port ${APP_PORT}..."
                        for i in \$(seq 1 30); do
                            status=\$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${APP_PORT}/api/v1/customers/123456/9999999999 || true)
                            if [ "\$status" = "200" ]; then
                                echo "App is up."
                                exit 0
                            fi
                            sleep 2
                        done
                        echo "App did not become ready in time."
                        cat app.log || true
                        exit 1
                    """
                }
            }
        }

        stage('Run API Tests') {
            steps {
                withMaven(
                    // Maven installation declared in the Jenkins "Global Tool Configuration"
                    maven: 'maven-3', // (1)
                    mavenLocalRepo: '.repository', // (2)
                    mavenSettingsConfig: 'my-maven-settings' // (3)
                ) {
                    sh '''
                    mvn -B test
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                // Kill the Spring Boot app and any child java process it spawned
                sh '''
                    if [ -f app/app.log ]; then
                        MVN_PID=$(cat app/app.log)
                        echo "Stopping app (mvn pid $MVN_PID) and its children..."
                        pkill -P $MVN_PID || true
                        kill $MVN_PID || true
                    fi
                    # Fallback in case the above misses the actual java process
                    pkill -f "spring-boot:run" || true
                '''
            }
            archiveArtifacts artifacts: 'app/app.log', allowEmptyArchive: true
        }
    }
}
