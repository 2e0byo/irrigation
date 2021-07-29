import gc
from sys import print_exception
import uasyncio as asyncio
from .clock import clockstr
import machine

errors = []


def log_print(*args):
    print(*args)
    with open("/app/static/test.log", "a") as f:
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
        with open("/app/static/test.log", "a") as f:
            print_exception(e, f)
        errors.append(e)


async def test_valve():
    from .hal import valve

    assert not valve.state
    valve.state = True
    await asyncio.sleep_ms(100)
    assert valve.en(), "Not enabled"
    assert valve.in1(), "Not in1"
    assert not valve.in2(), "in2"
    await asyncio.sleep(1)
    assert not valve.en(), "Still enabled"
    valve.state = False
    await asyncio.sleep_ms(100)
    assert valve.en(), "Not enabled"
    assert not valve.in1(), "in1"
    assert valve.in2(), "Not in2"
    await asyncio.sleep(1)
    assert not valve.en(), "Still enabled again"


tests = [test_valve]


async def run_tests():
    with open("/app/static/test.log", "w") as f:
        f.write("Test begins at {}\n".format(clockstr()))
    for test in tests:
        await run_test(test, test.__name__)

    if errors:
        log_print("\n\n---Errors:---\n\n")
        for e in errors:
            print_exception(e)
            with open("/app/static/test.log", "a") as f:
                print_exception(e, f)
        log_print("\n\n")

    else:
        log_print("\n\n---Success---\n\n")
        log_print("All tests passed\n\n")

    log_print("====Testing completed====")

    print("\n\nWill reboot in 60s")
    asyncio.get_event_loop().create_task(reboot_later())
    gc.collect()


async def reboot_later():
    await asyncio.sleep(60)
    print("Rebooting....")
    machine.reset()
