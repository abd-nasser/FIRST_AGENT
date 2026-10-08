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
ETAPE 2 défénir les models de données
'''

class Livreur(BaseModel):
    """ represente un livreur dans le système """
    id: int = Field(description='Identifiant unique du livreur') #La description est crucial plus tu decris bien , mieux le LLM comprend
    nom_complet: str = Field(description="Nom complet du livreur")
    ville: str = Field(description="Ville ou opère le livreur")
    zone : str = Field(description='Zone ou quartier couvert')
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
    
"""
ETAPE 3 les dépendances (Deps)
    on definie ce que l'agent à besoin pour fonctionner : une "session qui contient la base 
    de livreurs
"""

class AppSession(BaseModel):
    """Dépendances injectées dans l'agent."""
    livreurs : List[Livreur] = Field(default_factory=list, description="Liste des livreurs disponibles")
    demande_livraison : List[DemandeLivraison] = Field(default_factory=list, description="la liste des demandes de livraison")
    notification_envoyees : List[str] = Field(default_factory=list, description="Historique des notifications")
    

"""
    ETAPE 4 creer l'agent  
"""

agent = Agent(
    "openai:qwen2.5:7b",
    deps_type= AppSession,
    output_type=ResultatLivraison,
    system_prompt=(
        "Tu est 'Livre_SAMA' un assistant pour une plateforme de livraison."
        "Ton rôle est de trouver un livreur disponible dans le zone demandée,"
        "de le contacter, et de renvoyer un resultat structuré."
        "Utilise toujours les outils à ta disposition."
    ),
    
    
)


""" 
ETAPE 5 LES OUTILS (TOOLS)
on donne l'agent des fonction qu'il peut appeler 
"""

#outils 1 cherche un livreur
@agent.tool
def chercher_livreur(ctx: RunContext[AppSession], ville: str, zone: str ) -> List[Livreur]:
    """
    cherche un livreur disponible dans la ville ou zone données.
    retourne une liste de livreurs correspondants
    """
    resultats =  [
        l for l in ctx.deps.livreurs 
        if l.ville.lower() == ville.lower() 
        and l.zone.lower() == zone.lower()
        and l.disponible
        
        
    ]
    return resultats


#Outil 2 contacter livreur
@agent.tool
def contacter_livreur(ctx: RunContext[AppSession], livreur_id: int, message: str) -> str:
    """ 
    Contacte un livreur par son ID pour lui proposer une livraison.
    Retourne un message de confirmation
    """
    
    livreur = next( (l for l in ctx.deps.livreurs if l.id == livreur_id), None)
    
    if not livreur:
        return f"Livreur avec ID {livreur_id} introuvable"
    
    notification =  f"[{datetime.now()} SMS à {livreur.nom_complet} ({livreur.telephone}): {message}]"
    ctx.deps.notification_envoyees.append(notification)
    
    return f'Livreur{livreur.nom_complet} contacté avec succès'

##Outil 3 contacter livreurMarquer un livreur comme indisponible
@agent.tool
def marquer_indisponible(ctx: RunContext[AppSession], livreur_id: int) -> str:
    
    livreur = next((l for l in ctx.deps.livreurs if l.id == livreur_id ),None)
    if not livreur:
        return f"Livreur {livreur_id} introuvable"
    livreur.disponible = False
    return f'Livreur{livreur.nom_complet} marqué comme indisponible'


   

