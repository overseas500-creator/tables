const fs = require('fs');
let html = fs.readFileSync('index.html', 'utf8');

let replaced = false;
html = html.replace(/const preCheckBtn = document\.getElementById\("preCheckConflictsButton"\);\s*if \(preCheckBtn\) \{\s*preCheckBtn\.addEventListener\("click", \(\) => \{\s*const state = loadState\(\);/g, function(match) {
    replaced = true;
    return `const preCheckBtn = document.getElementById("preCheckConflictsButton");
            if (preCheckBtn) {
                preCheckBtn.addEventListener("click", () => {
                    // FIX: DO NOT shadow the global state variable by reloading from storage!
                    // This caused the pre-check to show default data if local storage wasn't synced.
                    // const state = loadState(); // REMOVED`;
});

if (replaced) {
    fs.writeFileSync('index.html', html);
    console.log('Successfully fixed preCheckBtn shadowing bug.');
} else {
    console.log('Failed to find preCheckBtn block.');
}
