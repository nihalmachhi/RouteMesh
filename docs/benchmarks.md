# Benchmark methodology

`make bench` runs the Locust workload against the local Compose stack and writes
raw measurements and a summary under `output/benchmarks/`. Run each policy with
the same duration and workload, and record the machine, configuration, and
commit alongside any comparison. The results are local observations, not
production throughput claims. Generated output is not checked in as a fixed
performance guarantee.
