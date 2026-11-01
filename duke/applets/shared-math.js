/**
 * SharedMath: Math Utilities, Parsing, and Axis Formatting
 */
const SharedMath = {
    // Allows implicit multiplication (2x, xy) and handles standard trig/log syntax
    formatImplicitMath: function(str) {
        let s = str.replace(/\s+/g, '');
        s = s.replace(/arcsin/gi, 'asin').replace(/arccos/gi, 'acos').replace(/arctan/gi, 'atan');
        s = s.replace(/arcsec/gi, 'asec').replace(/arccsc/gi, 'acsc').replace(/arccot/gi, 'acot');
        s = s.replace(/\|([^|]+)\|/g, 'abs($1)');
        s = s.replace(/log(?!10)/gi, 'log10').replace(/ln/gi, 'log');
        s = s.replace(/\/([0-9]*(?:[xy](?:\^[0-9.]+)?)+)/gi, '/($1)');
        s = s.replace(/xy/gi, 'x*y').replace(/yx/gi, 'y*x');
        s = s.replace(/([0-9])([xy\(])/gi, '$1*$2');
        s = s.replace(/([xy])([0-9])/gi, '$1*$2');
        s = s.replace(/([xy])(\()/gi, '$1*$2');
        s = s.replace(/(\))([xy0-9\(])/gi, '$1*$2');
        s = s.replace(/([0-9xy])(sin|cos|tan|asin|acos|atan|asec|acsc|acot|exp|log10|log|sqrt|abs|pi|e)/gi, '$1*$2');
        return s;
    },

    // Safely parses a math string, verifies allowed variables, and returns the compiled node + clean LaTeX
    parseEquation: function(exprStr, allowedVars) {
        let processed = this.formatImplicitMath(exprStr);
        let parsed = math.parse(processed);
        let isTrigMode = false;
        
        parsed.traverse(function(node, path, parent) {
            if (node.type === 'SymbolNode') {
                if (parent && parent.type === 'FunctionNode' && path === 'fn') return;
                if (!allowedVars.includes(node.name)) throw new Error(`Illegal variable: ${node.name}`);
            }
            if (node.type === 'FunctionNode' && ['sin', 'cos', 'tan', 'sec', 'csc', 'cot'].includes(node.fn.name)) {
                isTrigMode = true;
            }
        });

        let compiled = parsed.compile();
        let tex = parsed.toTex({ parenthesis: 'auto', implicit: 'hide' })
                        .replace(/\\log\left/g, '\\ln\\left')
                        .replace(/\\cdot\s*/g, '');
                        
        return { compiled, tex, isTrigMode };
    },

    // Generates mathematically clean tick marks for axes based on total span
    getStandardStep: function(span) {
        if (span > 500) return 100; if (span > 200) return 50; if (span > 100) return 20;
        if (span > 50) return 10; if (span > 20) return 5; if (span > 10) return 2;
        if (span > 5) return 1; if (span > 2) return 0.5; if (span > 1) return 0.2;
        return 0.1;
    }
};
