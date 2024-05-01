import re, argparse, sys, os
from datetime import datetime, timedelta

# configuration
expected_size = 5
cycle_usec = 1000

sample_rate = timedelta(microseconds=cycle_usec)
STRPTIME = "%Y/%m/%d,%H:%M:%S.%f"
STRFTIME = "%Y/%m/%d %H:%M:%S"
STRFTIME2 = "%Y/%m/%d %H:%M:%S.%f"

parser = argparse.ArgumentParser(
    prog="ActiData",
    description="Analyze Actimetre data"
)
parser.add_argument('-i', '--input',
                    help="Input file. Will use stdin if absent")
parser.add_argument('-o', '--output',
                    help="Output file. Will use stdout if absent")
parser.add_argument('-c', '--check', action='store_true',
                    help="Only check, no output")
parser.add_argument('-w', '--rewrite', action='store_true',
                    help="Rewrite input file. Meaningless if stdin is used")
parser.add_argument('-a', '--analyze', action='store_true',
                    help="Analyze timestamps (slow)")
args = parser.parse_args()

input = sys.stdin
output = sys.stdout

if args.input is None:
    print("Input : stdin", file=sys.stderr)
else:
    print(f"Input : {args.input}", file=sys.stderr)
    input = open(args.input, "r")
    if args.rewrite:
        tempfile = args.input + '.1'
        output = open(tempfile, "w")

if args.output is None:
    print("Output: stdout", file=sys.stderr)
else:
    print(f"Output: {args.output}", file=sys.stderr)
    if args.check or args.rewrite:
        print("Contradictory options", file=sys.stderr)
        exit(1)
    output = open(args.output, "w")

input_lines = 0
output_lines = 0
error_lines = 0
stopwatch = datetime.now()
prev_time = None
start_time = None
missing_time = timedelta(seconds=0)

actidata = re.compile(f"([0-9/]+,[0-9:]+.[0-9]+)(,[-+0-9.]+){{{expected_size}}}")
for line in input:
    line = line.strip()
    input_lines += 1
    if line == "":
        print(f"Empty line #{input_lines}", file=sys.stderr)
        continue
    matchdata = actidata.match(line)
    if matchdata is None:
        print(f"Regex doesn't match:\n{line}", file=sys.stderr)
        error_lines += 1
        continue
    else:
        # datalist = map(float, data_str)
        if not args.check:
            print(line, file=output)
        output_lines += 1

        if args.analyze:
            sample_time = datetime.strptime(matchdata.group(1), STRPTIME)
            if prev_time is not None:
                if sample_time - prev_time > sample_rate * cycle_usec:
                    missing = (sample_time - prev_time) // sample_rate - 1
                    print(f"Line #{input_lines}: missing {missing} measurements ({missing / cycle_usec :.3f}s) at " +
                          prev_time.strftime(STRFTIME2),
                          file=sys.stderr)
                    missing_time += timedelta(microseconds=missing * cycle_usec)
            prev_time = sample_time
            if start_time is None: start_time = sample_time

if input != sys.stdin:
    input.close()
if output != sys.stdout:
    output.close()
if args.rewrite:
    os.replace(tempfile, args.input)
print(f"Found {error_lines} errors", file=sys.stderr)

elapsed = datetime.now() - stopwatch
microseconds = elapsed.seconds * 1_000_000 + elapsed.microseconds
print(f"Input {input_lines} lines, output {output_lines} lines" +
      f" processed in {elapsed.seconds}s" +
      f" = {1_000 * input_lines / microseconds :.0f}klines/s",
      file=sys.stderr)

if args.analyze:
    span_time = sample_time - start_time
    recorded_time = span_time - missing_time
    recorded_cycles = (recorded_time.seconds * 1_000_000 + recorded_time.microseconds) / cycle_usec
    processing_speed = recorded_cycles * cycle_usec / microseconds
    print(f"Speed {processing_speed :.1f}x real-time" +
          f" ({3600 / processing_speed :.1f}s/hour)",
          file=sys.stderr)
    print(f"Time span {start_time.strftime(STRFTIME)} to {sample_time.strftime(STRFTIME)}" +
          f" with {missing_time.seconds}s ({100.0 * missing_time.seconds / span_time.seconds:.3f}%) missing" +
          f" = {recorded_time.seconds}s recorded" +
          f" -> {cycle_usec * output_lines / recorded_cycles :.2f}Hz",
          file=sys.stderr)

exit(error_lines)