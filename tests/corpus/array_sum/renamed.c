int calc_sum(int numbers[], int size) {
    int accum = 0;
    for (int idx = 0; idx < size; idx++) {
        accum = accum + numbers[idx];
    }
    return accum;
}