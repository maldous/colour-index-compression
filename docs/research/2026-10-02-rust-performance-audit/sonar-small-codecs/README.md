# Small codec Sonar refactor

Control-flow helpers preserve the existing BigUint arithmetic, candidate ordering, malformed-input errors, and cancellation checks. No format or algorithm changes were made. Qualification includes forced CIXG2 Huffman and context-range frames, plus CIXM6 context-type-class (mode 2) and histogram (mode 20) frames selected from real candidate comparisons.
