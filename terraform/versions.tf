terraform {
  # 1.11 es la primera versión con recursos efímeros y atributos write-only,
  # que se usan para que la contraseña de la base no quede en el estado
  required_version = ">= 1.11"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.6"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
  }
}
