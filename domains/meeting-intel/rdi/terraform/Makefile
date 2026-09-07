.PHONY: init plan apply destroy check

REDIS_SSL ?= false

ifndef REDIS_HOST
  -include $(CURDIR)/../../../../.env
  export
endif

TFVARS = -var="redis_host=$(REDIS_HOST)" \
	-var="redis_port=$(REDIS_PORT)" \
	-var="redis_username=$(REDIS_USERNAME)" \
	-var="redis_password=$(REDIS_PASSWORD)" \
	-var="redis_ssl=$(REDIS_SSL)"

check:
	@command -v gcloud >/dev/null || { echo "gcloud missing — cannot apply GKE terraform from this environment."; exit 2; }
	@command -v terraform >/dev/null || { echo "terraform missing — install Terraform >= 1.5."; exit 2; }
	@test -n "$(GOOGLE_CLOUD_PROJECT)$(TF_VAR_project_id)" -o -f terraform.tfvars || { \
	  echo "Set TF_VAR_project_id or copy terraform.tfvars.example to terraform.tfvars."; exit 2; }
	@test -n "$(REDIS_HOST)" || { echo "REDIS_HOST is not set; source .env or export it."; exit 2; }

init: check
	terraform init

plan: check
	terraform plan $(TFVARS)

apply: check
	terraform apply -auto-approve $(TFVARS)

destroy: check
	terraform destroy -auto-approve $(TFVARS)
