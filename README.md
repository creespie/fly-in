# fly-in
42 fly in project implementation


WORK IN PROGRESS


numero di mosse n
trovare percorso piu veloce e assegnarlo a 1 drone, rimuovere 1 spazio dalle caselle visitate.
salvare percorso in un array con numero di mosse annesso
ripetere finche non finiscono i droni o il numero di mosse n necessario non aumenta

se n aumenta i nodi hanno di nuovo tutto lo spazio che serve
riutilizzare tutti i percorsi salvati facendo aspettare per n - n.percorso turni

se non si trovano altri percorsi, ripetere percorsi salvati finche non finiscono i droni