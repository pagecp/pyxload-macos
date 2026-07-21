# PyXLoad pour macOS

Clone léger de `xload` écrit en Python. Cette configuration reproduit le
`xload` de kamari et ajoute un second graphe pour le GPU de l’Apple M4 Max.

## Installation

1. Si nécessaire, installer Python et tkinter avec MacPorts :

   ```bash
   sudo port install python314 py314-tkinter
   ```

2. Double-cliquer sur `install.command`.

   Si macOS refuse son ouverture, faire clic droit → **Ouvrir**, ou exécuter :

   ```bash
   chmod +x install.command uninstall.command
   ./install.command
   ```

Les deux fenêtres apparaissent immédiatement et reviendront automatiquement à
chaque ouverture de session. Leur dernière taille et position sont mémorisées :

- CPU : `150x100+1640+154`, étiquette `kamari` ;
- GPU : `150x100+1640+260`, étiquette `kamari GPU` ;
- police native `FixedRegular` taille 16 (rendu proche de la fonte X11
  bitmap `10x20` sur un écran Retina),
  mise à jour 3 s, grille magenta,
  fond noir, tracé blanc.

Le GPU est lu dans `IOGPU/PerformanceStatistics` avec `ioreg`, sans `sudo`.

Les fenêtres n'ont ni barre de titre ni contour. Pour les déplacer, faire
glisser directement le graphe. Le Ctrl-clic ouvre le menu permettant notamment
de quitter ou de désactiver temporairement le mode toujours au-dessus.

## Utilisation

- Redimensionner et déplacer la fenêtre normalement.
- Clic droit (ou Ctrl-clic) : garder au-dessus, réinitialiser l’échelle, quitter.
- `⌘Q` : quitter pour la session courante. Elle reviendra au prochain login.
- La grille magenta reste visible au-dessus de la surface blanche.
- Comme dans le widget Xaw `StripChart` utilisé par `xload`, l’échelle CPU vaut
  `int(charge maximale + 1)` lors d’un repaint. Pendant l’acquisition
  incrémentale, elle ne grandit que si la nouvelle valeur dépasse strictement
  l’échelle courante — y compris le cas historique subtil d’une valeur qui
  tombe exactement sur un entier. Chaque intervalle magenta représente
  toujours exactement une unité de load.
- Chaque mesure occupe exactement un pixel horizontal et chaque colonne du
  graphe est une barre verticale, comme dans `StripChart.c`. L’historique n’est
  jamais étiré pour remplir une fenêtre encore vide. Le défilement est d’un
  pixel par défaut et peut être changé avec `-jumpscroll`.
- Le GPU emploie le même redimensionnement dynamique, avec une unité de 10 %
  par intervalle afin que la petite fenêtre reste lisible.

## Fidélité à xload/Xaw

Le comportement a été revérifié directement dans `xload.c`, le fichier de
ressources `app-defaults/XLoad` et `StripChart.c` de libXaw : valeur CPU issue
du load average à 1 minute, première mesure après un intervalle, période par
défaut de 10 s (minimum 1 s), échelle minimale 1, une colonne remplie de 1 px
par mesure, `jumpScroll` de 1 px, réduction de l’échelle seulement après la
sortie de l’ancien maximum ou un repaint, lignes de référence entières et
étiquette placée hors de la zone du graphe.

Les différences volontaires sont la fenêtre macOS native sans décoration,
le déplacement et le menu contextuel, la mémorisation de position, l’option
de tracé non rempli et le graphe GPU. Les anciens modes X11 `-remote` (rwhod)
et `-lights` (LED du clavier) ne sont pas implémentés. L’installateur conserve
les réglages personnels de kamari (`-update 3`, 150×100, noir/blanc/magenta,
FixedRegular 16), tandis que les valeurs par défaut du programme suivent Xaw.

## Réglages

Les options sont visibles avec :

```bash
~/Applications/PyXLoad/pyxload.py --help
```

Exemple manuel :

```bash
python3 ~/Applications/PyXLoad/pyxload.py \
  -update 2 -scale 4 -geometry 800x220+20+80 --no-fill
```

Pour rendre ces options permanentes, ajouter les arguments comme éléments
`<string>...</string>` dans `ProgramArguments` du fichier :

```text
~/Library/LaunchAgents/com.page.pyxload.cpu.plist
~/Library/LaunchAgents/com.page.pyxload.gpu.plist
```

Puis recharger le LaunchAgent ou fermer et rouvrir la session.

## Désinstallation

Double-cliquer sur `uninstall.command`. Les fichiers sont déplacés dans la
Corbeille afin que l’opération reste récupérable.
