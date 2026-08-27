// Versão Definitiva - 2 registros por segundo e salvamento incremental otimizado
__config() -> {'scope' -> 'global'};

global_tracked_entity = null;
global_positions = [];

// Identifica a vaca assim que o script é carregado
vacas = entity_list('cow');

if (!vacas,
    print(format('r [Erro] Nenhuma vaca encontrada! Invoque a vaca primeiro e dê /script load tracker novamente.'));
,
    global_tracked_entity = vacas:0;
    global_positions = [];
    
    // Cria o arquivo do zero apenas com o cabeçalho no início do experimento
    write_file('dados_deambulacao', 'text', ['tick,pos_x,pos_y,pos_z']);
    print(format('g [Sucesso] Rastreamento de alta precisão (2Hz) iniciado!'));
);

// Executado a cada tick (20Hz)
__on_tick() -> (
    tempo_atual = tick_time();
    
    if (global_tracked_entity && !global_tracked_entity~'removed',
        
        // Exatamente como você pensou: coleta 2 vezes por segundo (a cada 10 ticks)
        if (tempo_atual % 10 == 0,
            pos = global_tracked_entity~'pos';
            nova_linha = str('%d,%.4f,%.4f,%.4f', tempo_atual, pos:0, pos:1, pos:2);
            put(global_positions, null, nova_linha);
        );
        
        // A cada 1 minuto (1200 ticks), joga o bloco acumulado para o arquivo e limpa a memória
        if (tempo_atual % 1200 == 0,
            if (length(global_positions) > 0,
                // O comando 'write_file' com uma lista anexa as linhas no final do arquivo existente
                write_file('dados_deambulacao', 'text', global_positions);
                
                // Limpa a lista da memória para o jogo nunca ter lag
                global_positions = [];
            );
        );
    );
);