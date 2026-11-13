terraform {
  backend "gcs" {
    # El bucket se pasa al iniciar: terraform init -backend-config="bucket=NOMBRE"
    prefix = "statsnostra-v5/estado"
  }
}
