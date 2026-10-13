int binary_search_for(int arr[], int n, int target) {
    int low = 0;
    int high = n - 1;
    for (; low <= high; ) {
        int mid = (low + high) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}