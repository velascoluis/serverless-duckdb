SERVICE_NAME=<TO_DO_DEVELOPER>
REGION=<TO_DO_DEVELOPER>
PROJECT_ID=<TO_DO_DEVELOPER>
gcloud config set project ${PROJECT_ID}
cd src
gcloud run deploy ${SERVICE_NAME} \
  --source . \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated


