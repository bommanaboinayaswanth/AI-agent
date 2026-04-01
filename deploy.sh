#!/bin/bash

# Azure Deployment Script
# This script deploys the AI Agent application to Azure

set -e

echo "=== AI Agent Deployment Script ==="

# Check prerequisites
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Set Azure subscription
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-ai-agent-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
APP_NAME="${AZURE_APP_NAME:-ai-agent-api}"
REGISTRY_NAME="${AZURE_REGISTRY_NAME:-aiagentregistry}"

echo "Subscription: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "App Name: $APP_NAME"

# Set subscription
az account set --subscription "$SUBSCRIPTION_ID"

# Create resource group
echo "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION"

# Create container registry
echo "Creating container registry..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$REGISTRY_NAME" \
    --sku Basic

# Build and push Docker image
echo "Building Docker image..."
docker build -t "$APP_NAME:latest" .

# Push to Azure Container Registry
REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"
az acr login --name "$REGISTRY_NAME"

echo "Pushing image to registry..."
docker tag "$APP_NAME:latest" "$REGISTRY_URL/$APP_NAME:latest"
docker push "$REGISTRY_URL/$APP_NAME:latest"

# Deploy using ARM template
echo "Deploying ARM template..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file azure/deploy.json \
    --parameters \
        appName="$APP_NAME" \
        location="$LOCATION" \
        containerImage="$REGISTRY_URL/$APP_NAME:latest"

# Get deployment outputs
APP_URL=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "deploy" \
    --query properties.outputs.appServiceUrl.value -o tsv)

echo "=== Deployment Complete ==="
echo "Application URL: $APP_URL"
echo "Container Registry: $REGISTRY_URL"
echo "Resource Group: $RESOURCE_GROUP"
