# Painel “Corrigir um registro”

Um único painel na Farm360 corrige colheita, descarte, adubação, custo, venda, recebimento e estoque.

- Lista os registros **atuais** do tipo escolhido (os já corrigidos não aparecem) e abre um formulário preenchido.
- **Motivo da correção**, quem corrigiu e a origem são obrigatórios. A correção cria um novo registro; o original fica no histórico e deixa de contar nos totais.
- Campo opcional deixado em branco é enviado como vazio (desconhecido), nunca como zero.
- Registro já corrigido por outra pessoa: o servidor responde 409; o painel avisa e atualiza a lista.
- Permissões são as do servidor: perfil sem acesso vê aviso, não botões escondidos.

Limites: não troca o talhão (colheita, descarte, adubação, custo) nem a venda de um recebimento; não mostra o histórico de versões. Testes: `frontend/src/features/corrections/`.
