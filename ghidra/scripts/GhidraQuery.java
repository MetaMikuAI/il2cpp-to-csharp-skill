// Query and decompile one function from a Ghidra project in GUI or headless mode.
//@category IL2CPP

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import ghidra.app.decompiler.ClangLine;
import ghidra.app.decompiler.ClangNode;
import ghidra.app.decompiler.ClangStatement;
import ghidra.app.decompiler.ClangSyntaxToken;
import ghidra.app.decompiler.ClangToken;
import ghidra.app.decompiler.ClangTokenGroup;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.PrettyPrinter;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Symbol;

public class GhidraQuery extends GhidraScript {

    private static final int DEFAULT_TIMEOUT_SECONDS = 120;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Usage: GhidraQuery.java <info|decompile|export|callees|callers|xrefs|disassemble> " +
                "<va:0x...|rva:0x...|name:exact-symbol> [timeout-for-decompile] " +
                "[artifact-path-for-export] [semantic-path-for-export]");
        }

        String action = args[0].toLowerCase();
        Address target = resolveTarget(args[1]);
        Function function = getFunctionAt(target);
        if (function == null) {
            function = getFunctionContaining(target);
        }

        println("=== GHIDRA_QUERY_BEGIN ===");
        println("program=" + currentProgram.getName());
        println("image_base=" + currentProgram.getImageBase());
        println("action=" + action);
        println("resolved_address=" + target);
        printSymbols(target);

        if ("xrefs".equals(action)) {
            printXrefs(target);
        }
        else {
            if (function == null) {
                throw new IllegalArgumentException("No function contains " + target);
            }
            printFunctionInfo(function);
            switch (action) {
                case "info":
                    break;
                case "decompile":
                    decompile(function, parseOptionalInt(args, 2, DEFAULT_TIMEOUT_SECONDS));
                    break;
                case "export":
                    if (args.length < 4) {
                        throw new IllegalArgumentException(
                            "export requires: <selector> <timeout-seconds> <artifact-path>");
                    }
                    exportDecompile(function, parseOptionalInt(args, 2, DEFAULT_TIMEOUT_SECONDS),
                        args[3], args.length > 4 ? args[4] : args[3] + ".semantic.tsv");
                    printFunctions("CALLEES", function.getCalledFunctions(monitor));
                    break;
                case "callees":
                    printFunctions("CALLEES", function.getCalledFunctions(monitor));
                    break;
                case "callers":
                    printFunctions("CALLERS", function.getCallingFunctions(monitor));
                    break;
                case "disassemble":
                    disassemble(target, function);
                    break;
                default:
                    throw new IllegalArgumentException("Unknown action: " + action);
            }
        }
        println("=== GHIDRA_QUERY_END ===");
    }

    private int parseOptionalInt(String[] args, int index, int defaultValue) {
        return args.length > index ? Integer.parseInt(args[index]) : defaultValue;
    }

    private long parseUnsigned(String text) {
        String value = text.trim();
        if (value.startsWith("0x") || value.startsWith("0X")) {
            return new BigInteger(value.substring(2), 16).longValue();
        }
        return new BigInteger(value, 10).longValue();
    }

    private Address resolveTarget(String selector) {
        if (selector.startsWith("va:")) {
            return toAddr(parseUnsigned(selector.substring(3)));
        }
        if (selector.startsWith("rva:")) {
            return currentProgram.getImageBase().add(parseUnsigned(selector.substring(4)));
        }
        String name = selector.startsWith("name:") ? selector.substring(5) : selector;
        for (Symbol symbol : currentProgram.getSymbolTable().getSymbols(name)) {
            if (!symbol.isExternal()) {
                return symbol.getAddress();
            }
        }
        throw new IllegalArgumentException("Exact symbol was not found: " + name);
    }

    private void printSymbols(Address address) {
        Symbol[] symbols = currentProgram.getSymbolTable().getSymbols(address);
        println("symbol_count=" + symbols.length);
        if (symbols.length == 0) {
            println("symbols=<none>");
            return;
        }
        for (Symbol symbol : symbols) {
            println("symbol=" + symbol.getName(true));
        }
    }

    private void printFunctionInfo(Function function) {
        println("function=" + function.getName(true));
        println("entry=" + function.getEntryPoint());
        println("body_min=" + function.getBody().getMinAddress());
        println("body_max=" + function.getBody().getMaxAddress());
        println("parameter_count=" + function.getParameterCount());
        println("thunk=" + function.isThunk());
    }

    private void decompile(Function function, int timeoutSeconds) {
        DecompInterface decompiler = new DecompInterface();
        try {
            DecompileResults results = runDecompiler(decompiler, function, timeoutSeconds);
            println("=== DECOMPILE_BEGIN ===");
            println(results.getDecompiledFunction().getC());
            println("=== DECOMPILE_END ===");
        }
        finally {
            decompiler.dispose();
        }
    }

    private void exportDecompile(Function function, int timeoutSeconds, String artifactPath,
            String semanticPath) {
        DecompInterface decompiler = new DecompInterface();
        try {
            DecompileResults results = runDecompiler(decompiler, function, timeoutSeconds);
            String cCode = results.getDecompiledFunction().getC();
            Path output = Paths.get(artifactPath).toAbsolutePath().normalize();
            Path parent = output.getParent();
            if (parent != null) {
                Files.createDirectories(parent);
            }
            byte[] bytes = cCode.getBytes(StandardCharsets.UTF_8);
            Files.write(output, bytes);
            println("decompile_complete=true");
            println("artifact=" + output);
            println("artifact_lines=" + countLines(cCode));
            println("artifact_bytes=" + bytes.length);
            println("artifact_sha256=" + sha256(bytes));
            exportSemanticIndex(function, results, semanticPath);
        }
        catch (Exception error) {
            throw new IllegalStateException("Could not export decompile: " + error.getMessage(), error);
        }
        finally {
            decompiler.dispose();
        }
    }

    private void exportSemanticIndex(Function function, DecompileResults results,
            String semanticPath) {
        try {
            ClangTokenGroup markup = results.getCCodeMarkup();
            if (markup == null) {
                throw new IllegalStateException("Decompiler returned no C markup");
            }
            List<ClangLine> lines = new PrettyPrinter(function, markup, null).getLines();
            List<ClangToken> tokens = new ArrayList<>();
            for (ClangLine line : lines) {
                tokens.addAll(line.getAllTokens());
            }

            Map<Integer, Integer> closingIndexes = new HashMap<>();
            List<Integer> braceStack = new ArrayList<>();
            for (int index = 0; index < tokens.size(); index++) {
                ClangToken token = tokens.get(index);
                if (!(token instanceof ClangSyntaxToken)) {
                    continue;
                }
                if ("{".equals(token.getText())) {
                    braceStack.add(index);
                }
                else if ("}".equals(token.getText()) && !braceStack.isEmpty()) {
                    int openIndex = braceStack.remove(braceStack.size() - 1);
                    closingIndexes.put(openIndex, index);
                }
            }
            if (!braceStack.isEmpty()) {
                throw new IllegalStateException("Decompiler markup contains unbalanced braces");
            }

            List<SemanticBlock> blocks = new ArrayList<>();
            for (int index = 0; index < tokens.size(); index++) {
                ClangToken token = tokens.get(index);
                if (!(token instanceof ClangSyntaxToken) || !"{".equals(token.getText())) {
                    continue;
                }
                Integer closeIndex = closingIndexes.get(index);
                if (closeIndex == null) {
                    throw new IllegalStateException("Decompiler markup contains an unmatched brace");
                }
                ClangStatement statement = containingStatement(token);
                int startLine = statementStartLine(
                    statement, token.getLineParent().getLineNumber());
                int endLine = tokens.get(closeIndex).getLineParent().getLineNumber();
                if (endLine <= startLine) {
                    continue;
                }
                String header = statement == null ?
                    PrettyPrinter.getText(token.getLineParent()).trim() : statement.toString().trim();
                HeaderInfo headerInfo = recoverWrappedHeader(lines, startLine, header);
                startLine = headerInfo.startLine;
                header = headerInfo.text;
                SemanticBlock parent = null;
                for (int prior = blocks.size() - 1; prior >= 0; prior--) {
                    SemanticBlock candidate = blocks.get(prior);
                    if (candidate.openIndex < index && candidate.closeIndex > closeIndex) {
                        parent = candidate;
                        break;
                    }
                }
                Address minAddress = null;
                Address maxAddress = null;
                for (int enclosed = index; enclosed <= closeIndex; enclosed++) {
                    ClangToken enclosedToken = tokens.get(enclosed);
                    Address tokenMin = enclosedToken.getMinAddress();
                    Address tokenMax = enclosedToken.getMaxAddress();
                    if (tokenMin != null && (minAddress == null || tokenMin.compareTo(minAddress) < 0)) {
                        minAddress = tokenMin;
                    }
                    if (tokenMax == null) {
                        tokenMax = tokenMin;
                    }
                    if (tokenMax != null && (maxAddress == null || tokenMax.compareTo(maxAddress) > 0)) {
                        maxAddress = tokenMax;
                    }
                }
                String id = String.format("B%04d", blocks.size() + 1);
                blocks.add(new SemanticBlock(id, classifyBlock(header, parent),
                    parent == null ? 0 : parent.depth + 1, parent == null ? "" : parent.id,
                    startLine, endLine, minAddress, maxAddress, header, index, closeIndex));
            }

            List<String> output = new ArrayList<>();
            output.add("block_id\tkind\tdepth\tparent\tstart_line\tend_line\tmin_address\tmax_address\theader");
            for (SemanticBlock block : blocks) {
                output.add(block.id + "\t" + block.kind + "\t" + block.depth + "\t" +
                    block.parent + "\t" + block.startLine + "\t" + block.endLine + "\t" +
                    addressText(block.minAddress) + "\t" + addressText(block.maxAddress) + "\t" +
                    escapeTsv(block.header));
            }
            Path outputPath = Paths.get(semanticPath).toAbsolutePath().normalize();
            Path parent = outputPath.getParent();
            if (parent != null) {
                Files.createDirectories(parent);
            }
            Files.write(outputPath, output, StandardCharsets.UTF_8);
            println("semantic_complete=true");
            println("semantic_artifact=" + outputPath);
            println("semantic_format=ghidra-markup-blocks-v1");
            println("semantic_blocks=" + blocks.size());
        }
        catch (Exception error) {
            println("semantic_complete=false");
            println("semantic_error=" + oneLine(error.getMessage()));
        }
    }

    private String classifyBlock(String header, SemanticBlock parent) {
        String normalized = header.replaceFirst("^[}\\s]+", "").trim();
        if (parent == null) {
            return "function";
        }
        if (normalized.matches("^else\\s+if\\b.*")) {
            return "else_if";
        }
        if (normalized.matches("^if\\b.*")) {
            return "if";
        }
        if (normalized.matches("^else\\b.*")) {
            return "else";
        }
        if (normalized.matches("^switch\\b.*")) {
            return "switch";
        }
        if (normalized.matches("^for\\b.*")) {
            return "for";
        }
        if (normalized.matches("^while\\b.*")) {
            return "while";
        }
        if (normalized.matches("^do\\b.*")) {
            return "do";
        }
        return "scope";
    }

    private HeaderInfo recoverWrappedHeader(List<ClangLine> lines, int startLine, String header) {
        if (isControlHeader(header) || startLine <= 1) {
            return new HeaderInfo(startLine, header);
        }
        for (int lineNumber = startLine - 1; lineNumber >= 1; lineNumber--) {
            String text = PrettyPrinter.getText(lines.get(lineNumber - 1)).trim();
            if (isControlHeader(text)) {
                StringBuilder joined = new StringBuilder();
                for (int current = lineNumber; current <= startLine; current++) {
                    String fragment = PrettyPrinter.getText(lines.get(current - 1)).trim();
                    if (!fragment.isEmpty()) {
                        if (joined.length() != 0) {
                            joined.append(' ');
                        }
                        joined.append(fragment);
                    }
                }
                return new HeaderInfo(lineNumber, joined.toString());
            }
            if (text.endsWith(";") || text.endsWith("{") || text.equals("}")) {
                break;
            }
        }
        return new HeaderInfo(startLine, header);
    }

    private boolean isControlHeader(String header) {
        String normalized = header.replaceFirst("^[}\\s]+", "").trim();
        return normalized.matches("^(else\\s+if|if|else|switch|for|while|do)\\b.*");
    }

    private ClangStatement containingStatement(ClangToken token) {
        ClangNode node = token.Parent();
        while (node != null) {
            if (node instanceof ClangStatement) {
                return (ClangStatement) node;
            }
            node = node.Parent();
        }
        return null;
    }

    private int statementStartLine(ClangStatement statement, int fallback) {
        if (statement == null) {
            return fallback;
        }
        List<ClangNode> nodes = new ArrayList<>();
        statement.flatten(nodes);
        int start = fallback;
        for (ClangNode node : nodes) {
            if (node instanceof ClangToken) {
                ClangLine line = ((ClangToken) node).getLineParent();
                if (line != null && line.getLineNumber() < start) {
                    start = line.getLineNumber();
                }
            }
        }
        return start;
    }

    private String addressText(Address address) {
        return address == null ? "" : address.toString();
    }

    private String escapeTsv(String text) {
        return text.replace("\\", "\\\\").replace("\t", "\\t")
            .replace("\r", "\\r").replace("\n", "\\n");
    }

    private String oneLine(String text) {
        if (text == null || text.isBlank()) {
            return "unknown semantic-index error";
        }
        return text.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ');
    }

    private static class SemanticBlock {
        final String id;
        final String kind;
        final int depth;
        final String parent;
        final int startLine;
        final int endLine;
        final Address minAddress;
        final Address maxAddress;
        final String header;
        final int openIndex;
        final int closeIndex;

        SemanticBlock(String id, String kind, int depth, String parent, int startLine,
                int endLine, Address minAddress, Address maxAddress, String header,
                int openIndex, int closeIndex) {
            this.id = id;
            this.kind = kind;
            this.depth = depth;
            this.parent = parent;
            this.startLine = startLine;
            this.endLine = endLine;
            this.minAddress = minAddress;
            this.maxAddress = maxAddress;
            this.header = header;
            this.openIndex = openIndex;
            this.closeIndex = closeIndex;
        }
    }

    private static class HeaderInfo {
        final int startLine;
        final String text;

        HeaderInfo(int startLine, String text) {
            this.startLine = startLine;
            this.text = text;
        }
    }

    private DecompileResults runDecompiler(DecompInterface decompiler, Function function,
            int timeoutSeconds) {
        decompiler.setOptions(new DecompileOptions());
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException("Decompiler initialization failed: " +
                decompiler.getLastMessage());
        }
        DecompileResults results =
            decompiler.decompileFunction(function, timeoutSeconds, monitor);
        if (!results.decompileCompleted() || results.getDecompiledFunction() == null) {
            throw new IllegalStateException("Decompile failed: " + results.getErrorMessage());
        }
        return results;
    }

    private int countLines(String text) {
        if (text.isEmpty()) {
            return 0;
        }
        int count = 0;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) == '\n') {
                count++;
            }
        }
        return text.endsWith("\n") ? count : count + 1;
    }

    private String sha256(byte[] bytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        StringBuilder hex = new StringBuilder();
        for (byte value : digest.digest(bytes)) {
            hex.append(String.format("%02x", value & 0xff));
        }
        return hex.toString();
    }

    private void printFunctions(String heading, Set<Function> functions) {
        List<Function> sorted = new ArrayList<>(functions);
        sorted.sort(Comparator.comparing(Function::getEntryPoint));
        println("=== " + heading + "_BEGIN ===");
        for (Function function : sorted) {
            println(function.getEntryPoint() + " " + function.getName(true));
        }
        println("=== " + heading + "_END ===");
    }

    private void printXrefs(Address target) {
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        println("=== XREFS_BEGIN ===");
        while (references.hasNext()) {
            Reference reference = references.next();
            Address from = reference.getFromAddress();
            Function owner = getFunctionContaining(from);
            println(from + " " + reference.getReferenceType() + " " +
                (owner == null ? "<no-function>" : owner.getName(true)));
        }
        println("=== XREFS_END ===");
    }

    private void disassemble(Address target, Function function) {
        Instruction containing = currentProgram.getListing().getInstructionContaining(target);
        Address start = containing == null ? target : containing.getAddress();
        InstructionIterator instructions =
            currentProgram.getListing().getInstructions(start, true);
        println("=== DISASSEMBLY_BEGIN ===");
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            if (!function.getBody().contains(instruction.getAddress())) {
                break;
            }
            println(instruction.getAddress() + "  " + instruction);
        }
        println("=== DISASSEMBLY_END ===");
    }
}
