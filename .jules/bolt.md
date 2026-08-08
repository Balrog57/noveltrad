## 2024-08-08 - Eliminate O(N) File I/O in Loop
**Learning:** Using a helper function that reads an entire file into memory (`Path.read_bytes()`) inside a loop over document chapters causes an O(N^2) I/O bottleneck, as the whole file is read from disk for every chapter chunk requested.
**Action:** Read the file bytes once into memory before the loop, and slice the byte array for each chapter.
