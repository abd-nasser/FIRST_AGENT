'''
ETAPE 1 les import et les modèles Pydantic
On commence par definir ce qu'on manipule ,
'''
import os  # Pour lire les variable d'environement les path etc..
from dotenv import load_dotenv  # charger le fichier .env (les bonnes pratique)
from pydantic import (BaseModel ,#Creer des structures de données
                      Field #pour ajouter des descriptions et validations
                      )
from pydantic_ai import Agent, RunContext #Les deux classe principales de pydanticAI
from typing import List, Optional #pour typer les listes et les champs optionnel 
from datetime import datetime # Pour horodater les commandes


'''
ETAPE défénir les models de données
'''

class Livreur(BaseModel):
    """ represente un livreur dans le système """
    id: int = Field(description='Identifiant unique du livreur') #La description est crucial plus tu decris bien , mieux le LLM comprend
    nom_compelt: str = Field(description="Nom complet du livreur")
    ville: str = Field(description="Ville ou opère le livreur")
    telephone: str = Field(description="Numéro de telephone")
    disponible: bool = Field(default=True, description="Statut de disponibilité")
    type_vehicule: str = Field(default="moto", description="type de vehicule")


class DemandeLivraison(BaseModel):
    client_nom: str = Field(description="Le nom du client qui demande la livraison")
    ville: str = Field(description="La ville de prise en charge")
    zone: str = Field(description="Zone ou quartier prise en charge")
    type_de_colis: str = Field(description="Type de colis : documents, colis, fragile, volumineux")
    poids_kg: float = Field(description="Poids approximatif en kg")
    urgence: bool = Field( default=False, description="Livraison urgente ou nom") 
    
    
class ResultatLivraison(BaseModel):
    """Resultat final après recherche et contact du livreur"""
    success: bool = Field(description="True si un livreur a été trouvé et contacté")
    livreur: Optional[Livreur] = Field(default=None, description='le Livreur Trouvé')
    message: str = Field(description="message de confirmation ou d'erreur")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")

