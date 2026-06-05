int main() {
    int i = 0;
    int sum = 0;
    int val = 0;
    int count = 0;
    
    // while
    while (i <= 10) {
        sum += i;
        i++;
    }
    printf("while sum 0..10: %d\n", sum);
    
    // for with break & continue
    for (i = 1; i <= 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        if (i > 7) {
            break;
        }
        val += i;
    }
    printf("for odd sum < 8: %d\n", val); // 1 + 3 + 5 + 7 = 16

    // do-while
    i = 0;
    do {
        count += 2;
        i++;
    } while (i < 5);
    printf("do-while count: %d\n", count); // 10
    
    return 0;
}
