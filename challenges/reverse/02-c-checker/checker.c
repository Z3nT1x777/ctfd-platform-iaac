/* CTF Reverse Challenge — License Checker
 * Key is split across three arrays to defeat naive string search.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Flag split into 3 parts — reassembled at runtime */
static const char p1[] = { 'C','T','F','{','c','o','m','p', 0 };
static const char p2[] = { 'a','r','e','_','h','a','r','d', 0 };
static const char p3[] = { 'c','o','d','e','d','}', 0 };

static int verify(const char *input) {
    char key[32] = {0};
    snprintf(key, sizeof(key), "%s%s%s", p1, p2, p3);
    return strcmp(input, key) == 0;
}

int main(void) {
    char buf[128] = {0};
    printf("License key: ");
    fflush(stdout);
    if (!fgets(buf, sizeof(buf) - 1, stdin)) return 1;
    buf[strcspn(buf, "\n")] = '\0';

    if (verify(buf)) {
        char key[32] = {0};
        snprintf(key, sizeof(key), "%s%s%s", p1, p2, p3);
        printf("[+] Valid! Flag: %s\n", key);
    } else {
        printf("[-] Invalid key.\n");
    }
    return 0;
}
