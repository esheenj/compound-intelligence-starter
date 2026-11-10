// Original synthetic aggregation, with no authorization or private data contracts.
package main

import (
    "bufio"
    "bytes"
    "fmt"
    "io"
    "os"
    "strconv"
)

var categories = []string{"atlas", "beacon", "cobalt", "delta"}
var kinds = []string{"PASS", "FAIL", "RETRY"}

type record struct { id string; category, kind int; value int64 }

func indexOf(values []string, target string) int {
    for index, value := range values { if value == target { return index } }
    return -1
}

func parseRecord(input []byte) (record, bool) {
    var empty record
    if len(input) > 256 { return empty, false }
    for _, c := range input { if c > 127 { return empty, false } }
    fields := bytes.Split(input, []byte{'\t'})
    if len(fields) != 4 { return empty, false }
    id := string(fields[0])
    if len(id) != 9 || id[0] != 'E' { return empty, false }
    for _, c := range []byte(id[1:]) { if c < '0' || c > '9' { return empty, false } }
    category, kind := indexOf(categories, string(fields[1])), indexOf(kinds, string(fields[2]))
    if category < 0 || kind < 0 { return empty, false }
    text := string(fields[3]); digits := text
    if len(digits) > 0 && digits[0] == '-' { digits = digits[1:] }
    if len(digits) == 0 || (len(digits) > 1 && digits[0] == '0') || text == "-0" { return empty, false }
    for _, c := range []byte(digits) { if c < '0' || c > '9' { return empty, false } }
    value, err := strconv.ParseInt(text, 10, 64)
    if err != nil || value < -10000 || value > 10000 { return empty, false }
    return record{id, category, kind, value}, true
}

func aggregate(input io.Reader) ([]byte, error) {
    seen := make(map[string]struct{})
    var counts [4][3]int64
    var sums [4][3]int64
    var accepted, duplicates, rejected int64
    reader := bufio.NewReader(input)
    for {
        line, err := reader.ReadBytes('\n')
        if len(line) > 0 {
            if line[len(line)-1] == '\n' { line = line[:len(line)-1] }
            rec, ok := parseRecord(line)
            if !ok { rejected++ } else if _, exists := seen[rec.id]; exists { duplicates++ } else {
                seen[rec.id] = struct{}{}
                accepted++
                counts[rec.category][rec.kind]++
                sums[rec.category][rec.kind] += rec.value
            }
        }
        if err == io.EOF { break }
        if err != nil { return nil, err }
    }
    var output bytes.Buffer
    fmt.Fprintf(&output, "ACCEPTED\t%d\nDUPLICATES\t%d\nREJECTED\t%d\n", accepted, duplicates, rejected)
    for ci, c := range categories {
        for ki, k := range kinds {
            fmt.Fprintf(&output, "GROUP\t%s\t%s\t%d\t%d\n", c, k, counts[ci][ki], sums[ci][ki])
        }
    }
    return output.Bytes(), nil
}

func main() {
    output, err := aggregate(os.Stdin)
    if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
    if _, err := os.Stdout.Write(output); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
}
