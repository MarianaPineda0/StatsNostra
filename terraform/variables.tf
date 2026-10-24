variable "project_id" {
  description = "ID del proyecto de GCP donde se crea la infraestructura"
  type        = string
  default     = "project-3f57bb8c-371e-4b9c-949"
}

variable "region" {
  description = "Región de GCP para los servicios regionales"
  type        = string
  default     = "us-central1"
}

variable "nombre" {
  description = "Prefijo de los recursos creados"
  type        = string
  default     = "statsnostra-v4"
}
