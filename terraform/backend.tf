terraform {
  backend "gcs" {
    # El bucket se pasa al iniciar: terraform init -backend-config="bucket=NOMBRE"
    prefix = "statsnostra/estado"
  }
}
