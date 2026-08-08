history = require('ai_ask.history')

item = history.create_item('test', 'enriched test')

print(vim.inspect(item))

item2 = history.create_item('test 2', 'enriched test 2')
print(vim.inspect(item2))

history.append_chunk_by_id(1, 'here ya go', 'answer')
history.append_chunk_by_id(2, 'its a me', 'answer')
history.append_chunk_by_id(2, 'mario', 'answer')

print(vim.inspect(item))
print(vim.inspect(item2))

history.mark_as(2, 'succeeded')
