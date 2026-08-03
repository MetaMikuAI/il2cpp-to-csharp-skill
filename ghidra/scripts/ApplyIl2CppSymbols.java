// Import Il2CppDumper script.json labels and function starts into Ghidra.
//@category IL2CPP

import java.io.File;
import java.io.FileReader;
import java.math.BigInteger;
import java.util.HashSet;
import java.util.Set;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import ghidra.app.cmd.function.ApplyFunctionSignatureCmd;
import ghidra.app.script.GhidraScript;
import ghidra.app.util.cparser.C.CParserUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.FunctionDefinitionDataType;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;
import ghidra.program.model.symbol.SymbolUtilities;

public class ApplyIl2CppSymbols extends GhidraScript {

    private JsonObject root;
    private Address imageBase;
    private boolean applySignatures;
    private int functionsCreated;
    private int methodLabelsCreated;
    private int metadataLabelsCreated;
    private int stringLabelsCreated;
    private int signaturesApplied;
    private int failures;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File scriptJson;
        if (args.length == 0) {
            if (isRunningHeadless()) {
                throw new IllegalArgumentException(
                    "Usage: ApplyIl2CppSymbols.java <script.json> [--signatures]");
            }
            scriptJson = askFile("Select Il2CppDumper script.json", "Open");
        }
        else {
            scriptJson = new File(args[0]);
        }

        if (!scriptJson.isFile()) {
            throw new IllegalArgumentException("script.json not found: " + scriptJson);
        }
        applySignatures = args.length > 1 && "--signatures".equals(args[1]);
        imageBase = currentProgram.getImageBase();

        try (FileReader reader = new FileReader(scriptJson)) {
            root = JsonParser.parseReader(reader).getAsJsonObject();
        }

        createFunctionStarts();
        applyMethodLabels();
        applyStrings();
        applyMetadata("ScriptMetadata");
        applyMetadata("ScriptMetadataMethod");
        if (applySignatures) {
            applyMethodSignatures();
        }

        println("IL2CPP import complete");
        println("  image base: " + imageBase);
        println("  functions created: " + functionsCreated);
        println("  method labels: " + methodLabelsCreated);
        println("  metadata labels: " + metadataLabelsCreated);
        println("  string labels: " + stringLabelsCreated);
        println("  signatures applied: " + signaturesApplied);
        println("  skipped/failed items: " + failures);
    }

    private JsonArray array(String key) {
        JsonElement value = root.get(key);
        return value != null && value.isJsonArray() ? value.getAsJsonArray() : new JsonArray();
    }

    private long parseOffset(JsonElement value) {
        if (value == null || value.isJsonNull()) {
            throw new IllegalArgumentException("missing address");
        }
        if (value.getAsJsonPrimitive().isNumber()) {
            return value.getAsLong();
        }
        String text = value.getAsString().trim();
        if (text.startsWith("0x") || text.startsWith("0X")) {
            return new BigInteger(text.substring(2), 16).longValue();
        }
        return new BigInteger(text, 10).longValue();
    }

    private Address addressOf(JsonObject item, String key) {
        return imageBase.add(parseOffset(item.get(key)));
    }

    private String labelName(JsonObject item) {
        String raw = item.get("Name").getAsString().replace(' ', '-');
        return SymbolUtilities.replaceInvalidChars(raw, false);
    }

    private void createFunctionStarts() {
        JsonArray addresses = array("Addresses");
        int count = Math.max(0, addresses.size() - 1); // final entry is commonly a sentinel
        monitor.initialize(count);
        monitor.setMessage("Creating IL2CPP function starts");
        for (int i = 0; i < count && !monitor.isCancelled(); i++) {
            try {
                Address address = imageBase.add(parseOffset(addresses.get(i)));
                if (getFunctionAt(address) == null) {
                    if (getInstructionAt(address) == null) {
                        disassemble(address);
                    }
                    Function created = createFunction(address, null);
                    if (created != null) {
                        functionsCreated++;
                    }
                }
            }
            catch (Exception exception) {
                failures++;
            }
            monitor.incrementProgress(1);
        }
    }

    private void applyMethodLabels() {
        JsonArray methods = array("ScriptMethod");
        Set<Long> namedFunctionAddresses = new HashSet<>();
        monitor.initialize(methods.size());
        monitor.setMessage("Applying IL2CPP method labels");
        for (JsonElement element : methods) {
            if (monitor.isCancelled()) {
                return;
            }
            try {
                JsonObject method = element.getAsJsonObject();
                Address address = addressOf(method, "Address");
                String name = labelName(method);
                Function function = getFunctionAt(address);
                if (function != null && namedFunctionAddresses.add(address.getOffset())) {
                    function.setName(name, SourceType.USER_DEFINED);
                }
                else {
                    createLabel(address, name, false, SourceType.USER_DEFINED);
                }
                methodLabelsCreated++;
            }
            catch (Exception exception) {
                failures++;
            }
            monitor.incrementProgress(1);
        }
    }

    private void applyStrings() {
        JsonArray strings = array("ScriptString");
        monitor.initialize(strings.size());
        monitor.setMessage("Applying IL2CPP string labels");
        int index = 1;
        for (JsonElement element : strings) {
            if (monitor.isCancelled()) {
                return;
            }
            try {
                JsonObject string = element.getAsJsonObject();
                Address address = addressOf(string, "Address");
                createLabel(address, "StringLiteral_" + index, false, SourceType.USER_DEFINED);
                setEOLComment(address, string.get("Value").getAsString());
                stringLabelsCreated++;
            }
            catch (Exception exception) {
                failures++;
            }
            index++;
            monitor.incrementProgress(1);
        }
    }

    private void applyMetadata(String key) {
        JsonArray records = array(key);
        monitor.initialize(records.size());
        monitor.setMessage("Applying " + key + " labels");
        for (JsonElement element : records) {
            if (monitor.isCancelled()) {
                return;
            }
            try {
                JsonObject record = element.getAsJsonObject();
                Address address = addressOf(record, "Address");
                String name = labelName(record);
                createLabel(address, name, false, SourceType.USER_DEFINED);
                setEOLComment(address, name);
                metadataLabelsCreated++;
            }
            catch (Exception exception) {
                failures++;
            }
            monitor.incrementProgress(1);
        }
    }

    private void applyMethodSignatures() {
        JsonArray methods = array("ScriptMethod");
        Set<Long> handledAddresses = new HashSet<>();
        monitor.initialize(methods.size());
        monitor.setMessage("Applying IL2CPP method signatures");
        for (JsonElement element : methods) {
            if (monitor.isCancelled()) {
                return;
            }
            try {
                JsonObject method = element.getAsJsonObject();
                Address address = addressOf(method, "Address");
                if (!handledAddresses.add(address.getOffset()) || !method.has("Signature")) {
                    monitor.incrementProgress(1);
                    continue;
                }
                String signature = method.get("Signature").getAsString().trim();
                if (signature.endsWith(";")) {
                    signature = signature.substring(0, signature.length() - 1);
                }
                FunctionDefinitionDataType parsed =
                    CParserUtils.parseSignature(null, currentProgram, signature, false);
                if (parsed != null && new ApplyFunctionSignatureCmd(
                    address, parsed, SourceType.USER_DEFINED, false, true).applyTo(currentProgram)) {
                    signaturesApplied++;
                }
                else {
                    failures++;
                }
            }
            catch (Exception exception) {
                failures++;
            }
            monitor.incrementProgress(1);
        }
    }
}
