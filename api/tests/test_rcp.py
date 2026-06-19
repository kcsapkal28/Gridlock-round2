import importlib.util, os
spec=importlib.util.spec_from_file_location("rcp", os.path.join(os.getcwd(),"rcp.py"))
rcp=importlib.util.module_from_spec(spec); spec.loader.exec_module(rcp)
def test_delay_math():
    assert abs(rcp.delay_minutes(600,0.5)-10.0)<1e-9   # 600s * 1.0 / 60 = 10 min
    assert rcp.delay_minutes(600,0.0)==0.0
def test_capacity_bounds():
    assert rcp.capacity_reduction(0,0)==0.10
    assert rcp.capacity_reduction(1,1)==0.60          # capped
    assert 0.10<rcp.capacity_reduction(0.5,0.2)<0.60
