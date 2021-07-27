import gc
from sys import print_exception
import uasyncio as asyncio

errors = []


def log_print(*args):
    print(*args)
    with open("/static/test.log", "a") as f:
        f.write("{}\n".format(" ".join(args)))


async def run_test(testfn, name):
    log_print("----Running test {}----".format(name))
    gc.collect()
    try:
        await testfn()
        log_print("Test completed")
    except Exception as e:
        log_print("Test {} raised exception".format(name))
        print_exception(e)
        with open("/static/test.log", "a") as f:
            print_exception(e, f)
        errors.append(e)


async def test_valve():
    from .hal import valve

    assert not valve.state
    valve.state = True
    assert valve.en
    assert valve.in1
    assert not valve.in2
    await asyncio.sleep(1)
    assert not valve.en
    valve.state = False
    assert valve.en
    assert not valve.in1
    assert valve.in2
    await asyncio.sleep(1)
    assert not valve.en


tests = [test_valve]


async def run_tests():
    for test in tests:
        await run_test(test, test.__name__)
