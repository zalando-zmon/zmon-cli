import pytest


@pytest.fixture(params=[
    (
        'my-app-1-[staging_1:v1]@1.2.3',
        'my-app-1-[staging_1:v1]@1.2.3'
    ),
    (
        'my-app-1-(staging:v1)',
        'my-app-1-[staging:v1]'
    ),
    (
        'my-app-1-(staging:v1)/metrics',
        'my-app-1-[staging:v1]-metrics'
    ),
    (
        'my-app-1-(staging:v1)/metrics%=^&$#*+=?<>,ß',
        'my-app-1-[staging:v1]-metrics-'
    ),
    (
        'my-app-1-(((staging:v1)))/#api/metrics%=^&$#',
        'my-app-1-[staging:v1]-api-metrics-'
    ),
    (
        'my-app-1-(((staging:v1)))/metrics%=^&$#()',
        'my-app-1-[staging:v1]-metrics-[]'
    ),
    (
        'my app        1 ( staging )( )',
        'my-app-1-[-staging-][-]'
    ),
    (
        'MY APP 1 / metrics',
        'my-app-1-metrics'
    ),
])
def fx_ids(request):
    return request.param
