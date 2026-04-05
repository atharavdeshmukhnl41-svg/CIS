## Root Cause Analysis Priority Logic

The RCA engine checks conditions in this order:

1. NSG + Route Table both blocking
2. Load Balancer backend + rule both missing
3. **Route Table blackhole routes** (Priority 94)
4. Load Balancer backend missing (Priority 90)
5. **Load Balancer listener missing** (Priority 90) ← CIP matches here
6. NSG blocking
7. No external ingress path
8. Metrics issue + VM running
9. **VM power state not running** (Priority 87) ← CIP1 matches here
10. Metrics issue

## Why CIP vs CIP1 show different root causes:

**CIP VM Analysis Path:**
```
PublicIP → LoadBalancer → NIC → VM → NSG → RouteTable → Metrics
           ↑ LB listener issue found ✗ first
           
Result: "Load Balancer listener missing for port 22"
Confidence: 90
```

**CIP1 VM Analysis Path:**
```
PublicIP → [NO LoadBalancer] → NIC → VM → NSG → RouteTable → Metrics
                 ↑ Skipped (LB not in topology)
           
           VM power state issue found ✗ first
           
Result: "VM is not in a running power state"
Confidence: 87
```

## The Key Difference:

- **CIP**: Has a Load Balancer in its network topology → LB configuration issues are detected first
- **CIP1**: Does NOT have a Load Balancer → VM state issues are detected first

Both VMs are DOWN, but the RCA identifies different BLOCKING COMPONENTS:
- CIP is blocked by LB configuration
- CIP1 is blocked by VM not being in running state
