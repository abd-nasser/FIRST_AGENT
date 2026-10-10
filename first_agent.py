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
from typing import List, Optional , Literal#pour typer les listes et les champs optionnel 
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
    livreur: Optional[Livreur] = Field(default=None, description='le Livreur Trouvé')
    status: Literal["en_attente", "accepter", "refuser"] = Field(default="en_attente", description="détermine le status de la demande de livraison")
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

load_dotenv()

agent = Agent(
    "openai:qwen2.5:7b",
    deps_type= AppSession,
    output_type=ResultatLivraison,
    system_prompt=(
    "Tu es 'Livre_SAMA', un assistant pour une plateforme de livraison. "
    "Ton rôle est de : "
    "1. Trouver un livreur disponible dans la zone demandée. "
    "2. Le contacter pour lui proposer la livraison. "
    "3. Le marquer comme indisponible après acceptation. "
    "4. Créer une demande de livraison en base de données. "
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


## Outils 4 creer la demande
@agent.tool
def creer_demande_livraison(
    ctx: RunContext[AppSession],
    ville: str,
    zone: str,
    livreur_id: Optional[int] = None,
    client_nom: Optional[str] = None,
    type_de_colis: Optional[str] = None,
    poids_kg: Optional[float] = None,
) -> str:
    """
    Crée une demande de livraison en base de données.
    Si un livreur est disponible, la demande est acceptée.
    Sinon, elle reste en attente.
    """
    # 1. Chercher le livreur
    livreur = None
    if livreur_id is not None:
        livreur = next(
            (l for l in ctx.deps.livreurs if l.id == livreur_id and l.disponible),
            None
        )
    
    # 2. Déterminer le statut
    if livreur is None:
        status = "en_attente"
        message = "Demande de livraison en attente : aucun livreur disponible."
    else:
        status = "accepter"
        message = f"Demande créée avec le livreur {livreur.nom}."
    
    # 3. Créer la demande
    demande_livraison = DemandeLivraison(
        client_nom=client_nom or "Non fourni",
        ville=ville.lower(),
        zone=zone.lower(),
        type_de_colis=type_de_colis or "Non spécifié",
        poids_kg=poids_kg if poids_kg is not None else 1.0,
        livreur=livreur,
        status=status,
    )
    
    # 4. Sauvegarder (simulation)
    ctx.deps.demandes.append(demande_livraison)
    
    return message
       
    


if __name__ == "__main__":
     # Création de quelques livreurs de test
    livreurs_test = [
        Livreur(id=1, nom_complet="Moussa", ville="Ouagadougou", zone="Zone du Bois", telephone="70 00 00 01"),
        Livreur(id=2, nom_complet="Fatou", ville="Ouagadougou", zone="Zone du Bois", telephone="70 00 00 02"),
        Livreur(id=3, nom_complet="Ibrahim", ville="Ouagadougou", zone="Gounghin", telephone="70 00 00 03"),
        Livreur(id=4, nom_complet="Awa", ville="Bobo-Dioulasso", zone="Secteur 1", telephone="70 00 00 04"),
    ]
    
    session = AppSession(livreurs=livreurs_test)
    
     # Demande de livraison
    demande = (
        "Bonjour, je m'appelle Alice. J'ai un colis fragile à livrer "
        "dans la Zone du Bois à Ouagadougou. C'est assez urgent. "
        "Trouve-moi un livreur disponible et contacte-le."
    )
    
    
    resultat = agent.run_sync(demande, deps=session)
    
    print('=' * 50)
    print("RESULTAT de l'AGENT")
    print('=' * 50)
    print(f'succès:{resultat.output.success}')
    print (f'Message:{resultat.output.message}')  
    if resultat.output.livreur:
        print(f"Livreur : {resultat.output.livreur.nom_complet} ({resultat.output.livreur.telephone}) ")
    print(f"Timestamp: {resultat.output.timestamp}")
    
    print('=' * 50)
    print("NOTIFICATIONS ENVOYEES")
    for notif in session.notification_envoyees:
        print(f'- {notif}')
        
    print('=' * 50)
    for dmd in session.demande_livraison:
        print(f" demande de livraison pour client -{dmd.client_nom if dmd.client_nom else "pas de nom"} - status= {dmd.status}")
    
      
    

   

