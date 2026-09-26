"""Moteur de questions de QuestionnApp.

Brique autonome : elle reçoit un modèle de question (JSON) et une graine, et
produit une instance (énoncé + champs de réponse), puis corrige des réponses.
Elle est utilisée par le serveur via un sous-processus (voir runner.py) avec un
protocole JSON sur stdin/stdout, ce qui permet de la réutiliser depuis n'importe
quelle autre stack (PHP, Java, Node...).
"""
