box.cfg{
    listen = 3301,
    wal_mode = 'none'
}

box.schema.space.create('votings', {if_not_exists = true})
box.space.votings:format({
        {name = 'id', type = 'string'},
        {name = 'creator', type = 'string'},
        {name = 'question', type = 'string'},
        {name = 'options', type = 'map'},
        {name = 'votes', type = 'map'},
        {name = 'is_active', type = 'boolean'},
        {name = 'channel_id', type = 'string'}
})

-- Индекс по ID голосования
box.space.votings:create_index('primary', {
    type = 'hash',
    parts = {'id'},
    if_not_exists = true
})

box.schema.space.create('voted_users', {if_not_exists = true})
box.space.voted_users:format({
    {name = 'voting_id', type = 'string'},
    {name = 'user_id', type = 'string'}
})

box.space.voted_users:create_index('primary', {
    type = 'hash',
    parts = {'voting_id', 'user_id'},
    if_not_exists = true
})

print("Tarantool initialization completed!")