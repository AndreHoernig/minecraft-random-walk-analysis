# Análise do movimento de mobs no Minecraft como processo difusivo

Este repositório contém os scripts utilizados na investigação do movimento de um mob passivo no Minecraft como um processo difusivo.
Aqui neste README você encontra instruções introdutórias.

### Pré-requisitos

- Minecraft Java Edition
- Fabric Loader
- [Carpet Mod](https://github.com/gnembon/fabric-carpet)
- Prims Launcher (opcional, é uma alternativa que roda bem o tracker)
  
### Como usar o script `tracker.sc`

1. Coloque o arquivo `tracker.sc` em uma das pastas:
   - `saves/[SEU_MUNDO]/scripts/` (apenas para esse mundo)
   - `config/carpet/scripts/` (para todos os mundos)

2. No jogo, dê um nome ao mob que deseja rastrear (use uma name tag ou o comando `/name`).

3. Carregue o script no chat com o comando "/script load tracker".

4. O script começará a registrar a posição do mob a cada tick (20 vezes por segundo) e salvará os dados em um arquivo `dados_mob.txt`.

5. Para interromper, utilize o comando "/script unload tracker", via chat do jogo.

### Onde encontrar os dados

6. O arquivo `dados_mob.txt` será salvo na mesma pasta onde o script foi colocado (dentro da pasta `scripts/` do mundo ou na pasta global).

### Análise dos dados com Python

7. Salve o arquivo dados_mob.txt em algum local fácil de encontrar e comece a fazer as análises com Python (os arquivos "dados_mob.txt" e "analise_mob.py" precisam estar na mesma pasta). Os códigos que eu elaborei para o manuscrito da RBEF estão disponíveis para uso livre aqui no meu repositório no GitHub. Ao rodar o código, salvará as imagens na mesma pasta.


Tendo dúvidas e interesse, sinta-se livre para entrar em contato via: andre.hoernig@gmail.com.
