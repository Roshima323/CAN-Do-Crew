
#!/bin/sh

DURATION=10

i=1
while [ "$i" -le "$DURATION" ]; do
    echo "Elapsed time: ${i}s"
    sleep 1
    i=$((i + 1))
done


