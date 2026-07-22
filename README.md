# fly-in
42 fly in project implementation


WORK IN PROGRESS


registrare numero di percorsi massimo pari al numero di droni
ogni percorso tiene al massimo la capacita' piu piccola sia di celle che di connessioni
funzione che calcola quanti turni da un punto a un altro seguendo un percorso memorizzato
usare percorso piu breve finche la ripetizione non supera la differenza con il pu breve successivo
valutare quanto si overlappano i percorsi, e se si arriva in posizioni sensibili in contemporanea o meno
movimento per zona restricted solo se la successiva puo essere liberata in tempo
coefficiente di priorita, scegliere a pari mosse quello con priorita piu altra

algoritmo
dijkstra per il piu efficiente, dividere per la capienza per avere un valore effettivo per drone
opzioni: 
capienza resta uguale o diminuisce nel tempo: solo dijkstra e altri percorsi indipendenti

capienza aumenta dopo un po, sneza diminuzione successiva: dijkstra o yen da dove aumentano verso l'inizio, senza usare il piu efficiente originale e fino a massima capienza del ottimizzato. se poi l'ottimizzato aumenta ulteriormente, nuovo dijkstra o yen e limitare la capienza dei nodi gia usati nel secondo percorso o bloccarli. 