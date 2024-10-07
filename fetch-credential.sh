#! /bin/bash

echo "Authenticating to GitGuardian via Trusted Publishing"

API_KEY="$(python /app/oidc-exchange.py)"

echo "GITGUARDIAN_API_KEY=$API_KEY" >> $GITHUB_ENV
