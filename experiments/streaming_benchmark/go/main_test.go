package main

import (
    "strings"
    "testing"
)

func TestCanonicalRecord(t *testing.T) {
    if _, ok := parseRecord([]byte("E00000001\tatlas\tPASS\t-10000")); !ok {
        t.Fatal("valid record rejected")
    }
    for _, input := range []string{
        "E00000001\tatlas\tPASS\t+5",
        "E00000001\tatlas\tPASS\t-0",
        "E00000001\tatlas\tPASS\t01",
        "E00000001\tatlas\tPASS\t10001",
        "E00000001\tatlas\tPASS\t0\textra",
        "E00000001\tunknown\tPASS\t0",
    } {
        if _, ok := parseRecord([]byte(input)); ok { t.Fatalf("unexpectedly valid: %q", input) }
    }
}

func TestAggregation(t *testing.T) {
    input := "E00000001\tatlas\tPASS\t5\nE00000001\tatlas\tPASS\t7\nbad\n"
    result, err := aggregate(strings.NewReader(input))
    if err != nil || !strings.HasPrefix(string(result), "ACCEPTED\t1\nDUPLICATES\t1\nREJECTED\t1\n") {
        t.Fatalf("got %s, %v", string(result), err)
    }
}
