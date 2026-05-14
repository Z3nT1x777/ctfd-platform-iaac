/* CTF Reverse Challenge — XOR Checker
 * The expected key is XOR-ed byte by byte with a repeating mask.
 * Reverse the XOR to find the original string.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* XOR mask (4-byte repeating) */
static const unsigned char mask[] = { 0x42, 0x4c, 0x55, 0x45 }; /* "BLUE" */

/* Expected bytes = flag XOR mask (repeating) */
/* flag = CTF{xor_repeating_key_weak} (27 chars) */
static const unsigned char expected[] = {
    0x01, 0x18, 0x13, 0x3e, /* C^B T^L F^U {^E */
    0x3a, 0x23, 0x27, 0x1a, /* x^B o^L r^U _^E */
    0x30, 0x29, 0x25, 0x20, /* r^B e^L p^U e^E */
    0x23, 0x38, 0x3c, 0x2b, /* a^B t^L i^U n^E */
    0x25, 0x13, 0x3e, 0x20, /* g^B _^L k^U e^E */
    0x3b, 0x13, 0x22, 0x20, /* y^B _^L w^U e^E */
    0x23, 0x27, 0x28        /* a^B k^L }^U     */
};

static int verify(const char *input) {
    size_t len = sizeof(expected);
    if (strlen(input) != len) return 0;
    for (size_t i = 0; i < len; i++) {
        if (((unsigned char)input[i] ^ mask[i % 4]) != expected[i])
            return 0;
    }
    return 1;
}

int main(void) {
    char buf[128] = {0};
    printf("Enter the secret key: ");
    fflush(stdout);
    if (!fgets(buf, sizeof(buf) - 1, stdin)) return 1;
    buf[strcspn(buf, "\n")] = '\0';

    if (verify(buf)) {
        printf("[+] Correct! Flag: %s\n", buf);
    } else {
        printf("[-] Wrong key.\n");
    }
    return 0;
}
