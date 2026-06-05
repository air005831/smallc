int main() {
    int score = 85;
    int age = 15;

    if (score >= 90) {
        printf("A\n");
    } else if (score >= 80) {
        printf("B\n");
    } else if (score >= 70) {
        printf("C\n");
    } else {
        printf("F\n");
    }
    
    if (age >= 18) {
        printf("Adult\n");
    } else {
        printf("Minor\n");
    }
    return 0;
}
