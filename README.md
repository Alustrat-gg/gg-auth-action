# gg-auth-action
The action uses the GitHub OIDC token to ask GitGuardian to generate a short-life token. It then saves it inside the job GitHub environment variables so it can be used in the following job's steps.
