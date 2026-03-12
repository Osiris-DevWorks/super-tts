import json

with open('tichro.json', 'r') as f:
    kss = json.load(f)

ttl_dims = kss['style_ttl']['dims']  # [1, 50, 256]
dp_dims = kss['style_dp']['dims']    # [1, 8, 16]

def reshape_flat_to_3d(flat_data, dims):
    d0, d1, d2 = dims
    result = []
    idx = 0
    for i in range(d0):
        batch = []
        for j in range(d1):
            row = flat_data[idx:idx+d2]
            batch.append(row)
            idx += d2
        result.append(batch)
    return result

ttl_3d = reshape_flat_to_3d(kss['style_ttl']['data'], ttl_dims)
dp_3d = reshape_flat_to_3d(kss['style_dp']['data'], dp_dims)

updated = {
    'style_ttl': {
        'dims': ttl_dims,
        'data': ttl_3d,
        'type': 'float32'
    },
    'style_dp': {
        'dims': dp_dims,
        'data': dp_3d,
        'type': 'float32'
    }
}

with open('tichro_updated.json', 'w') as f:
    json.dump(updated, f)