void sort_array(int list[], int size) {
    for (int step = 0; step < size - 1; step++) {
        for (int idx = 0; idx < size - step - 1; idx++) {
            if (list[idx] > list[idx + 1]) {
                int swap_val = list[idx];
                list[idx] = list[idx + 1];
                list[idx + 1] = swap_val;
            }
        }
    }
}